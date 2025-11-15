"""Content-Based Recommendation Algorithm"""

import numpy as np
from typing import List, Dict, Tuple, Set
from sqlalchemy.orm import Session
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter

from ..models import Item, Interaction
from ..config import settings


class ContentBasedService:
    """
    Content-Based Filtering using item features

    Uses TF-IDF vectorization on item descriptions and tags
    to compute item similarity and make recommendations.
    """

    def __init__(self, db: Session):
        self.db = db
        self.tfidf_vectorizer = TfidfVectorizer(
            max_features=500,
            stop_words='english',
            ngram_range=(1, 2)
        )
        self.item_features_matrix = None
        self.item_similarity_matrix = None
        self.item_id_to_idx = {}
        self.idx_to_item_id = {}

    def build_item_features(self) -> np.ndarray:
        """Build TF-IDF feature matrix for all items"""

        items = self.db.query(Item).all()

        if not items:
            return np.array([])

        # Create mapping
        self.item_id_to_idx = {item.id: idx for idx, item in enumerate(items)}
        self.idx_to_item_id = {v: k for k, v in self.item_id_to_idx.items()}

        # Combine text features for each item
        item_texts = []
        for item in items:
            # Combine title, description, category, and tags
            text_parts = [item.title or ""]

            if item.description:
                text_parts.append(item.description)

            if item.category:
                text_parts.append(item.category)

            if item.tags:
                text_parts.append(" ".join(item.tags))

            combined_text = " ".join(text_parts)
            item_texts.append(combined_text)

        # Create TF-IDF matrix
        self.item_features_matrix = self.tfidf_vectorizer.fit_transform(item_texts)

        return self.item_features_matrix

    def compute_item_similarity(self) -> np.ndarray:
        """Compute item-item similarity matrix using cosine similarity"""

        if self.item_features_matrix is None:
            self.build_item_features()

        # Compute cosine similarity
        self.item_similarity_matrix = cosine_similarity(self.item_features_matrix)

        # Set diagonal to 0
        np.fill_diagonal(self.item_similarity_matrix, 0)

        return self.item_similarity_matrix

    def get_similar_items(self, item_id: int, top_n: int = 10) -> List[Tuple[int, float]]:
        """
        Get similar items based on content similarity

        Args:
            item_id: Source item ID
            top_n: Number of similar items to return

        Returns:
            List of tuples (item_id, similarity_score)
        """

        if self.item_similarity_matrix is None:
            self.compute_item_similarity()

        item_idx = self.item_id_to_idx.get(item_id)
        if item_idx is None:
            return []

        # Get similarity scores for this item
        similarities = self.item_similarity_matrix[item_idx]

        # Get top-n similar items
        similar_indices = np.argsort(similarities)[-top_n:][::-1]

        similar_items = [
            (self.idx_to_item_id[idx], similarities[idx])
            for idx in similar_indices
            if similarities[idx] > 0
        ]

        return similar_items

    def get_recommendations(
        self, user_id: int, top_n: int = 10, exclude_interacted: bool = True
    ) -> List[Tuple[int, float]]:
        """
        Get content-based recommendations for a user

        Recommends items similar to items the user has previously interacted with.

        Args:
            user_id: Target user ID
            top_n: Number of recommendations to return
            exclude_interacted: Whether to exclude items user has already interacted with

        Returns:
            List of tuples (item_id, score)
        """

        if self.item_similarity_matrix is None:
            self.compute_item_similarity()

        # Get user's interactions
        interactions = (
            self.db.query(Interaction)
            .filter(Interaction.user_id == user_id)
            .all()
        )

        if not interactions:
            # User has no history, return popular items
            return self._get_popular_items(top_n)

        # Get interacted items with weights
        interacted_items = {}
        for interaction in interactions:
            item_id = interaction.item_id
            weight = interaction.rating if interaction.rating else interaction.weight

            # Aggregate multiple interactions
            if item_id in interacted_items:
                interacted_items[item_id] = max(interacted_items[item_id], weight)
            else:
                interacted_items[item_id] = weight

        # Calculate scores for all items based on similarity to interacted items
        item_scores = {}

        for item_id, weight in interacted_items.items():
            item_idx = self.item_id_to_idx.get(item_id)
            if item_idx is None:
                continue

            # Get similarities to all other items
            similarities = self.item_similarity_matrix[item_idx]

            for target_idx, similarity in enumerate(similarities):
                if similarity > 0:
                    target_item_id = self.idx_to_item_id[target_idx]

                    # Weight similarity by user's interaction strength
                    score = similarity * weight

                    if target_item_id in item_scores:
                        item_scores[target_item_id] += score
                    else:
                        item_scores[target_item_id] = score

        # Exclude already interacted items if requested
        if exclude_interacted:
            interacted_item_ids = set(interacted_items.keys())
            item_scores = {k: v for k, v in item_scores.items() if k not in interacted_item_ids}

        # Sort by score and return top-n
        sorted_items = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_n]

    def get_recommendations_by_category(
        self, user_id: int, category: str, top_n: int = 10
    ) -> List[Tuple[int, float]]:
        """
        Get content-based recommendations filtered by category

        Args:
            user_id: Target user ID
            category: Item category to filter by
            top_n: Number of recommendations to return

        Returns:
            List of tuples (item_id, score)
        """

        # Get all recommendations
        all_recommendations = self.get_recommendations(user_id, top_n * 5, exclude_interacted=True)

        # Filter by category
        category_recommendations = []
        for item_id, score in all_recommendations:
            item = self.db.query(Item).filter(Item.id == item_id).first()
            if item and item.category == category:
                category_recommendations.append((item_id, score))
                if len(category_recommendations) >= top_n:
                    break

        return category_recommendations

    def _get_popular_items(self, top_n: int = 10) -> List[Tuple[int, float]]:
        """
        Get popular items (fallback for cold start)

        Args:
            top_n: Number of items to return

        Returns:
            List of tuples (item_id, popularity_score)
        """

        items = (
            self.db.query(Item)
            .order_by(Item.popularity_score.desc())
            .limit(top_n)
            .all()
        )

        return [(item.id, item.popularity_score) for item in items]
