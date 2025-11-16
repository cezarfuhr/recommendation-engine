"""Hybrid Recommendation Algorithm"""

import numpy as np
from typing import List, Tuple, Dict
from sqlalchemy.orm import Session
from collections import defaultdict

from .collaborative_filtering import CollaborativeFilteringService
from .content_based import ContentBasedService
from ..config import settings


class HybridRecommendationService:
    """
    Hybrid recommendation combining collaborative filtering and content-based filtering

    Uses a weighted combination of both approaches to leverage the strengths of each:
    - Collaborative filtering: Good for finding unexpected items based on similar users
    - Content-based: Good for recommending similar items and handling new items
    """

    def __init__(self, db: Session, alpha: float = None):
        """
        Initialize hybrid recommendation service

        Args:
            db: Database session
            alpha: Weight for collaborative filtering (1-alpha for content-based)
                  If None, uses value from settings
        """
        self.db = db
        self.alpha = alpha if alpha is not None else settings.HYBRID_ALPHA
        self.collaborative_service = CollaborativeFilteringService(db)
        self.content_based_service = ContentBasedService(db)

    def get_recommendations(
        self,
        user_id: int,
        top_n: int = 10,
        exclude_interacted: bool = True,
        method: str = "weighted"
    ) -> List[Tuple[int, float]]:
        """
        Get hybrid recommendations

        Args:
            user_id: Target user ID
            top_n: Number of recommendations to return
            exclude_interacted: Whether to exclude items user has already interacted with
            method: Combination method - 'weighted', 'rank', or 'cascade'

        Returns:
            List of tuples (item_id, score)
        """

        if method == "weighted":
            return self._weighted_hybrid(user_id, top_n, exclude_interacted)
        elif method == "rank":
            return self._rank_hybrid(user_id, top_n, exclude_interacted)
        elif method == "cascade":
            return self._cascade_hybrid(user_id, top_n, exclude_interacted)
        else:
            return self._weighted_hybrid(user_id, top_n, exclude_interacted)

    def _weighted_hybrid(
        self, user_id: int, top_n: int, exclude_interacted: bool
    ) -> List[Tuple[int, float]]:
        """
        Weighted hybrid approach

        Combines scores from both algorithms using weighted average:
        final_score = alpha * collaborative_score + (1 - alpha) * content_score
        """

        # Get recommendations from both services
        # Request more to have enough after normalization
        collaborative_recs = self.collaborative_service.get_recommendations(
            user_id, top_n * 3, method="hybrid", exclude_interacted=exclude_interacted
        )
        content_recs = self.content_based_service.get_recommendations(
            user_id, top_n * 3, exclude_interacted=exclude_interacted
        )

        # Normalize scores to [0, 1] range
        collab_scores = self._normalize_scores(dict(collaborative_recs))
        content_scores = self._normalize_scores(dict(content_recs))

        # Combine scores
        all_items = set(collab_scores.keys()) | set(content_scores.keys())
        hybrid_scores = {}

        for item_id in all_items:
            collab_score = collab_scores.get(item_id, 0)
            content_score = content_scores.get(item_id, 0)

            # Weighted combination
            hybrid_scores[item_id] = (
                self.alpha * collab_score + (1 - self.alpha) * content_score
            )

        # Sort and return top-n
        sorted_items = sorted(hybrid_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_n]

    def _rank_hybrid(
        self, user_id: int, top_n: int, exclude_interacted: bool
    ) -> List[Tuple[int, float]]:
        """
        Rank-based hybrid approach

        Combines ranks from both algorithms rather than raw scores.
        This gives more equal weight to both methods regardless of score scales.
        """

        # Get recommendations from both services
        collaborative_recs = self.collaborative_service.get_recommendations(
            user_id, top_n * 3, method="hybrid", exclude_interacted=exclude_interacted
        )
        content_recs = self.content_based_service.get_recommendations(
            user_id, top_n * 3, exclude_interacted=exclude_interacted
        )

        # Convert to rank-based scores (higher rank = better)
        collab_ranks = {
            item_id: len(collaborative_recs) - rank
            for rank, (item_id, _) in enumerate(collaborative_recs)
        }
        content_ranks = {
            item_id: len(content_recs) - rank
            for rank, (item_id, _) in enumerate(content_recs)
        }

        # Combine ranks
        all_items = set(collab_ranks.keys()) | set(content_ranks.keys())
        hybrid_ranks = {}

        for item_id in all_items:
            collab_rank = collab_ranks.get(item_id, 0)
            content_rank = content_ranks.get(item_id, 0)

            # Weighted combination of ranks
            hybrid_ranks[item_id] = (
                self.alpha * collab_rank + (1 - self.alpha) * content_rank
            )

        # Sort and return top-n
        sorted_items = sorted(hybrid_ranks.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_n]

    def _cascade_hybrid(
        self, user_id: int, top_n: int, exclude_interacted: bool
    ) -> List[Tuple[int, float]]:
        """
        Cascade hybrid approach

        Uses collaborative filtering first, then fills gaps with content-based.
        Good for leveraging collaborative when available, falling back to content-based.
        """

        # Start with collaborative filtering
        collaborative_recs = self.collaborative_service.get_recommendations(
            user_id, top_n, method="hybrid", exclude_interacted=exclude_interacted
        )

        # If we have enough, return them
        if len(collaborative_recs) >= top_n:
            return collaborative_recs

        # Otherwise, supplement with content-based
        recommended_items = {item_id for item_id, _ in collaborative_recs}
        content_recs = self.content_based_service.get_recommendations(
            user_id, top_n * 2, exclude_interacted=exclude_interacted
        )

        # Add content-based recommendations that aren't already recommended
        for item_id, score in content_recs:
            if item_id not in recommended_items:
                collaborative_recs.append((item_id, score * 0.8))  # Slightly lower score
                recommended_items.add(item_id)

                if len(collaborative_recs) >= top_n:
                    break

        return collaborative_recs[:top_n]

    def _normalize_scores(self, scores: Dict[int, float]) -> Dict[int, float]:
        """
        Normalize scores to [0, 1] range using min-max normalization

        Args:
            scores: Dictionary of item_id -> score

        Returns:
            Dictionary of item_id -> normalized_score
        """

        if not scores:
            return {}

        values = list(scores.values())
        min_score = min(values)
        max_score = max(values)

        # Avoid division by zero
        if max_score == min_score:
            return {k: 1.0 for k in scores.keys()}

        # Min-max normalization
        normalized = {
            k: (v - min_score) / (max_score - min_score)
            for k, v in scores.items()
        }

        return normalized

    def explain_recommendation(
        self, user_id: int, item_id: int
    ) -> Dict[str, float]:
        """
        Explain why an item was recommended

        Returns the contribution of each algorithm to the final score.

        Args:
            user_id: User ID
            item_id: Item ID

        Returns:
            Dictionary with algorithm contributions
        """

        # Get scores from both algorithms
        collaborative_recs = dict(
            self.collaborative_service.get_recommendations(user_id, 100, method="hybrid")
        )
        content_recs = dict(
            self.content_based_service.get_recommendations(user_id, 100)
        )

        collab_score = collaborative_recs.get(item_id, 0)
        content_score = content_recs.get(item_id, 0)

        # Normalize
        all_collab_scores = self._normalize_scores(collaborative_recs)
        all_content_scores = self._normalize_scores(content_recs)

        norm_collab_score = all_collab_scores.get(item_id, 0)
        norm_content_score = all_content_scores.get(item_id, 0)

        final_score = (
            self.alpha * norm_collab_score + (1 - self.alpha) * norm_content_score
        )

        return {
            "collaborative_raw_score": collab_score,
            "content_raw_score": content_score,
            "collaborative_normalized_score": norm_collab_score,
            "content_normalized_score": norm_content_score,
            "collaborative_contribution": self.alpha * norm_collab_score,
            "content_contribution": (1 - self.alpha) * norm_content_score,
            "final_score": final_score,
            "alpha": self.alpha,
        }
