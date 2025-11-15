"""Collaborative Filtering Recommendation Algorithm"""

import numpy as np
from typing import List, Dict, Tuple
from sqlalchemy.orm import Session
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict

from ..models import User, Item, Interaction
from ..config import settings


class CollaborativeFilteringService:
    """
    User-based and Item-based Collaborative Filtering

    Implements both user-based and item-based collaborative filtering
    using cosine similarity for finding similar users/items.
    """

    def __init__(self, db: Session):
        self.db = db
        self.k_neighbors = settings.COLLABORATIVE_K_NEIGHBORS
        self.user_item_matrix = None
        self.user_similarity_matrix = None
        self.item_similarity_matrix = None

    def build_user_item_matrix(self) -> np.ndarray:
        """Build user-item interaction matrix"""

        # Get all interactions
        interactions = self.db.query(Interaction).all()

        # Get unique users and items
        users = self.db.query(User).all()
        items = self.db.query(Item).all()

        user_id_to_idx = {user.id: idx for idx, user in enumerate(users)}
        item_id_to_idx = {item.id: idx for idx, item in enumerate(items)}

        # Initialize matrix
        matrix = np.zeros((len(users), len(items)))

        # Fill matrix with interaction weights or ratings
        for interaction in interactions:
            user_idx = user_id_to_idx.get(interaction.user_id)
            item_idx = item_id_to_idx.get(interaction.item_id)

            if user_idx is not None and item_idx is not None:
                # Use rating if available, otherwise use weighted interaction
                value = interaction.rating if interaction.rating else interaction.weight
                matrix[user_idx, item_idx] = value

        self.user_item_matrix = matrix
        self.user_id_to_idx = user_id_to_idx
        self.item_id_to_idx = item_id_to_idx
        self.idx_to_user_id = {v: k for k, v in user_id_to_idx.items()}
        self.idx_to_item_id = {v: k for k, v in item_id_to_idx.items()}

        return matrix

    def compute_user_similarity(self) -> np.ndarray:
        """Compute user-user similarity matrix using cosine similarity"""

        if self.user_item_matrix is None:
            self.build_user_item_matrix()

        # Cosine similarity between users
        self.user_similarity_matrix = cosine_similarity(self.user_item_matrix)

        # Set diagonal to 0 (a user is not similar to themselves for recommendation purposes)
        np.fill_diagonal(self.user_similarity_matrix, 0)

        return self.user_similarity_matrix

    def compute_item_similarity(self) -> np.ndarray:
        """Compute item-item similarity matrix using cosine similarity"""

        if self.user_item_matrix is None:
            self.build_user_item_matrix()

        # Cosine similarity between items (transpose the matrix)
        self.item_similarity_matrix = cosine_similarity(self.user_item_matrix.T)

        # Set diagonal to 0
        np.fill_diagonal(self.item_similarity_matrix, 0)

        return self.item_similarity_matrix

    def get_user_based_recommendations(
        self, user_id: int, top_n: int = 10, exclude_interacted: bool = True
    ) -> List[Tuple[int, float]]:
        """
        Get recommendations using user-based collaborative filtering

        Args:
            user_id: Target user ID
            top_n: Number of recommendations to return
            exclude_interacted: Whether to exclude items user has already interacted with

        Returns:
            List of tuples (item_id, score)
        """

        if self.user_similarity_matrix is None:
            self.compute_user_similarity()

        # Get user index
        user_idx = self.user_id_to_idx.get(user_id)
        if user_idx is None:
            return []

        # Get similar users
        user_similarities = self.user_similarity_matrix[user_idx]

        # Get top-k similar users
        similar_user_indices = np.argsort(user_similarities)[-self.k_neighbors:][::-1]

        # Predict ratings for all items
        item_scores = defaultdict(float)
        similarity_sums = defaultdict(float)

        for similar_user_idx in similar_user_indices:
            similarity = user_similarities[similar_user_idx]
            if similarity <= 0:
                continue

            # Get items this similar user has interacted with
            for item_idx, rating in enumerate(self.user_item_matrix[similar_user_idx]):
                if rating > 0:
                    item_id = self.idx_to_item_id[item_idx]
                    item_scores[item_id] += similarity * rating
                    similarity_sums[item_id] += similarity

        # Normalize scores
        for item_id in item_scores:
            if similarity_sums[item_id] > 0:
                item_scores[item_id] /= similarity_sums[item_id]

        # Exclude already interacted items if requested
        if exclude_interacted:
            interacted_items = set()
            for item_idx, rating in enumerate(self.user_item_matrix[user_idx]):
                if rating > 0:
                    interacted_items.add(self.idx_to_item_id[item_idx])

            item_scores = {k: v for k, v in item_scores.items() if k not in interacted_items}

        # Sort by score and return top-n
        sorted_items = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_n]

    def get_item_based_recommendations(
        self, user_id: int, top_n: int = 10, exclude_interacted: bool = True
    ) -> List[Tuple[int, float]]:
        """
        Get recommendations using item-based collaborative filtering

        Args:
            user_id: Target user ID
            top_n: Number of recommendations to return
            exclude_interacted: Whether to exclude items user has already interacted with

        Returns:
            List of tuples (item_id, score)
        """

        if self.item_similarity_matrix is None:
            self.compute_item_similarity()

        # Get user index
        user_idx = self.user_id_to_idx.get(user_id)
        if user_idx is None:
            return []

        # Get items user has interacted with
        user_ratings = self.user_item_matrix[user_idx]
        interacted_item_indices = np.where(user_ratings > 0)[0]

        if len(interacted_item_indices) == 0:
            return []

        # Calculate scores for all items
        item_scores = defaultdict(float)

        for item_idx in interacted_item_indices:
            user_rating = user_ratings[item_idx]

            # Get similar items
            item_similarities = self.item_similarity_matrix[item_idx]

            # Add weighted similarities
            for target_item_idx, similarity in enumerate(item_similarities):
                if similarity > 0:
                    target_item_id = self.idx_to_item_id[target_item_idx]
                    item_scores[target_item_id] += similarity * user_rating

        # Exclude already interacted items if requested
        if exclude_interacted:
            interacted_items = {self.idx_to_item_id[idx] for idx in interacted_item_indices}
            item_scores = {k: v for k, v in item_scores.items() if k not in interacted_items}

        # Sort by score and return top-n
        sorted_items = sorted(item_scores.items(), key=lambda x: x[1], reverse=True)
        return sorted_items[:top_n]

    def get_recommendations(
        self, user_id: int, top_n: int = 10, method: str = "hybrid", exclude_interacted: bool = True
    ) -> List[Tuple[int, float]]:
        """
        Get collaborative filtering recommendations

        Args:
            user_id: Target user ID
            top_n: Number of recommendations to return
            method: 'user' for user-based, 'item' for item-based, 'hybrid' for both
            exclude_interacted: Whether to exclude items user has already interacted with

        Returns:
            List of tuples (item_id, score)
        """

        if method == "user":
            return self.get_user_based_recommendations(user_id, top_n, exclude_interacted)
        elif method == "item":
            return self.get_item_based_recommendations(user_id, top_n, exclude_interacted)
        else:  # hybrid
            # Combine both methods
            user_recs = self.get_user_based_recommendations(user_id, top_n * 2, exclude_interacted)
            item_recs = self.get_item_based_recommendations(user_id, top_n * 2, exclude_interacted)

            # Merge and average scores
            combined_scores = defaultdict(list)
            for item_id, score in user_recs:
                combined_scores[item_id].append(score)
            for item_id, score in item_recs:
                combined_scores[item_id].append(score)

            # Average the scores
            final_scores = {k: np.mean(v) for k, v in combined_scores.items()}
            sorted_items = sorted(final_scores.items(), key=lambda x: x[1], reverse=True)

            return sorted_items[:top_n]
