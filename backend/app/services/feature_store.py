"""Feature Store implementation"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from redis import Redis
import json

from ..models import User, Item, Interaction
from ..config import settings
from ..utils.logging import get_logger

logger = get_logger(__name__)


class FeatureStore:
    """
    Simple Feature Store for managing and serving features

    Provides consistent feature computation and caching for both
    training and serving.
    """

    def __init__(self, db: Session, redis_client: Optional[Redis] = None):
        self.db = db
        self.redis = redis_client or Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=4,  # Separate DB for feature store
            decode_responses=True
        )
        self.feature_ttl = 3600  # 1 hour TTL for features

    # User Features

    def get_user_features(self, user_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get feature vector for a user

        Args:
            user_id: User ID
            use_cache: Whether to use cached features

        Returns:
            Dictionary of user features
        """
        cache_key = f"features:user:{user_id}"

        # Try cache first
        if use_cache:
            cached = self.redis.get(cache_key)
            if cached:
                logger.debug(f"User features cache hit for user {user_id}")
                return json.loads(cached)

        logger.debug(f"Computing user features for user {user_id}")

        # Compute features
        user = self.db.query(User).filter(User.id == user_id).first()
        if not user:
            return {}

        # Get user interactions
        interactions = self.db.query(Interaction).filter(
            Interaction.user_id == user_id
        ).all()

        # Compute features
        features = {
            "user_id": user_id,
            "total_interactions": len(interactions),
            "interaction_types": self._count_interaction_types(interactions),
            "avg_rating": self._compute_avg_rating(interactions),
            "favorite_categories": self._compute_favorite_categories(user_id),
            "activity_score": self._compute_activity_score(interactions),
            "recency_score": self._compute_recency_score(interactions),
            "account_age_days": (datetime.utcnow() - user.created_at).days,
            "preferences": user.preferences,
            "computed_at": datetime.utcnow().isoformat()
        }

        # Cache features
        self.redis.setex(cache_key, self.feature_ttl, json.dumps(features))

        return features

    def get_user_features_batch(self, user_ids: List[int]) -> pd.DataFrame:
        """
        Get features for multiple users as DataFrame

        Args:
            user_ids: List of user IDs

        Returns:
            DataFrame with user features
        """
        features_list = []

        for user_id in user_ids:
            features = self.get_user_features(user_id)
            features_list.append(features)

        return pd.DataFrame(features_list)

    # Item Features

    def get_item_features(self, item_id: int, use_cache: bool = True) -> Dict[str, Any]:
        """
        Get feature vector for an item

        Args:
            item_id: Item ID
            use_cache: Whether to use cached features

        Returns:
            Dictionary of item features
        """
        cache_key = f"features:item:{item_id}"

        # Try cache first
        if use_cache:
            cached = self.redis.get(cache_key)
            if cached:
                logger.debug(f"Item features cache hit for item {item_id}")
                return json.loads(cached)

        logger.debug(f"Computing item features for item {item_id}")

        # Compute features
        item = self.db.query(Item).filter(Item.id == item_id).first()
        if not item:
            return {}

        # Get item interactions
        interactions = self.db.query(Interaction).filter(
            Interaction.item_id == item_id
        ).all()

        # Compute features
        features = {
            "item_id": item_id,
            "title": item.title,
            "category": item.category,
            "tags": item.tags,
            "total_interactions": len(interactions),
            "avg_rating": self._compute_avg_rating(interactions),
            "popularity_score": item.popularity_score,
            "view_count": self._count_interaction_type(interactions, "view"),
            "click_count": self._count_interaction_type(interactions, "click"),
            "purchase_count": self._count_interaction_type(interactions, "purchase"),
            "age_days": (datetime.utcnow() - item.created_at).days,
            "features": item.features,
            "computed_at": datetime.utcnow().isoformat()
        }

        # Cache features
        self.redis.setex(cache_key, self.feature_ttl, json.dumps(features))

        return features

    def get_item_features_batch(self, item_ids: List[int]) -> pd.DataFrame:
        """
        Get features for multiple items as DataFrame

        Args:
            item_ids: List of item IDs

        Returns:
            DataFrame with item features
        """
        features_list = []

        for item_id in item_ids:
            features = self.get_item_features(item_id)
            features_list.append(features)

        return pd.DataFrame(features_list)

    # User-Item Interaction Features

    def get_user_item_features(
        self, user_id: int, item_id: int, use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Get contextual features for user-item pair

        Args:
            user_id: User ID
            item_id: Item ID
            use_cache: Whether to use cached features

        Returns:
            Dictionary of user-item features
        """
        cache_key = f"features:user_item:{user_id}:{item_id}"

        # Try cache first
        if use_cache:
            cached = self.redis.get(cache_key)
            if cached:
                return json.loads(cached)

        # Get individual features
        user_features = self.get_user_features(user_id, use_cache)
        item_features = self.get_item_features(item_id, use_cache)

        # Check if user has interacted with this item
        has_interacted = self.db.query(Interaction).filter(
            Interaction.user_id == user_id,
            Interaction.item_id == item_id
        ).first() is not None

        # Check if user likes this category
        favorite_categories = user_features.get("favorite_categories", [])
        item_category = item_features.get("category")
        category_match = item_category in favorite_categories if item_category else False

        # Combine features
        features = {
            "user_id": user_id,
            "item_id": item_id,
            "has_interacted": has_interacted,
            "category_match": category_match,
            "user_activity_score": user_features.get("activity_score", 0),
            "item_popularity_score": item_features.get("popularity_score", 0),
            "computed_at": datetime.utcnow().isoformat()
        }

        # Cache features (shorter TTL for contextual features)
        self.redis.setex(cache_key, 300, json.dumps(features))  # 5 minutes

        return features

    # Helper methods

    def _count_interaction_types(self, interactions: List[Interaction]) -> Dict[str, int]:
        """Count interactions by type"""
        counts = {}
        for interaction in interactions:
            interaction_type = interaction.interaction_type
            counts[interaction_type] = counts.get(interaction_type, 0) + 1
        return counts

    def _count_interaction_type(self, interactions: List[Interaction], interaction_type: str) -> int:
        """Count specific interaction type"""
        return sum(1 for i in interactions if i.interaction_type == interaction_type)

    def _compute_avg_rating(self, interactions: List[Interaction]) -> float:
        """Compute average rating from interactions"""
        ratings = [i.rating for i in interactions if i.rating is not None]
        return np.mean(ratings) if ratings else 0.0

    def _compute_favorite_categories(self, user_id: int, top_n: int = 3) -> List[str]:
        """Compute user's favorite categories"""
        # Get all items user interacted with
        interactions = self.db.query(Interaction).filter(
            Interaction.user_id == user_id
        ).all()

        # Count categories
        category_counts = {}
        for interaction in interactions:
            item = self.db.query(Item).filter(Item.id == interaction.item_id).first()
            if item and item.category:
                category_counts[item.category] = category_counts.get(item.category, 0) + 1

        # Sort and return top categories
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in sorted_categories[:top_n]]

    def _compute_activity_score(self, interactions: List[Interaction]) -> float:
        """
        Compute user activity score

        Higher score = more active user
        """
        if not interactions:
            return 0.0

        # Count recent interactions (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_interactions = [
            i for i in interactions
            if i.created_at >= thirty_days_ago
        ]

        # Score based on total and recent activity
        total_score = min(len(interactions) / 100.0, 1.0)  # Cap at 100
        recent_score = min(len(recent_interactions) / 30.0, 1.0)  # Cap at 30

        return (total_score * 0.4 + recent_score * 0.6)

    def _compute_recency_score(self, interactions: List[Interaction]) -> float:
        """
        Compute recency score

        Higher score = more recent activity
        """
        if not interactions:
            return 0.0

        # Get most recent interaction
        most_recent = max(interactions, key=lambda x: x.created_at)
        days_since = (datetime.utcnow() - most_recent.created_at).days

        # Exponential decay: score decreases over time
        # After 30 days, score is ~0.5, after 90 days ~0.2
        return np.exp(-days_since / 30.0)

    # Cache management

    def invalidate_user_features(self, user_id: int) -> None:
        """Invalidate cached features for a user"""
        cache_key = f"features:user:{user_id}"
        self.redis.delete(cache_key)
        logger.debug(f"Invalidated user features cache for user {user_id}")

    def invalidate_item_features(self, item_id: int) -> None:
        """Invalidate cached features for an item"""
        cache_key = f"features:item:{item_id}"
        self.redis.delete(cache_key)
        logger.debug(f"Invalidated item features cache for item {item_id}")

    def invalidate_all_features(self) -> None:
        """Invalidate all cached features"""
        pattern = "features:*"
        keys = self.redis.keys(pattern)
        if keys:
            self.redis.delete(*keys)
        logger.info(f"Invalidated {len(keys)} feature cache entries")
