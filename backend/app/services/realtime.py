"""Real-time Update Service using Redis"""

import json
import redis
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

from ..config import settings


class RealtimeUpdateService:
    """
    Real-time recommendation updates using Redis

    Handles caching of recommendations and real-time updates
    as users interact with items.
    """

    def __init__(self):
        self.redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            password=settings.REDIS_PASSWORD,
            decode_responses=True
        )
        self.cache_ttl = settings.CACHE_TTL

    def cache_recommendations(
        self,
        user_id: int,
        algorithm: str,
        recommendations: List[Dict[str, Any]],
        ttl: Optional[int] = None
    ) -> bool:
        """
        Cache recommendations for a user

        Args:
            user_id: User ID
            algorithm: Algorithm name
            recommendations: List of recommendation dictionaries
            ttl: Time to live in seconds (optional, uses default if not provided)

        Returns:
            True if successful, False otherwise
        """

        try:
            key = self._get_cache_key(user_id, algorithm)
            value = json.dumps({
                "recommendations": recommendations,
                "cached_at": datetime.utcnow().isoformat(),
                "algorithm": algorithm
            })

            ttl = ttl or self.cache_ttl
            self.redis_client.setex(key, ttl, value)
            return True

        except Exception as e:
            print(f"Error caching recommendations: {e}")
            return False

    def get_cached_recommendations(
        self, user_id: int, algorithm: str
    ) -> Optional[List[Dict[str, Any]]]:
        """
        Get cached recommendations for a user

        Args:
            user_id: User ID
            algorithm: Algorithm name

        Returns:
            List of recommendations or None if not found
        """

        try:
            key = self._get_cache_key(user_id, algorithm)
            value = self.redis_client.get(key)

            if value:
                data = json.loads(value)
                return data.get("recommendations")

            return None

        except Exception as e:
            print(f"Error getting cached recommendations: {e}")
            return None

    def invalidate_user_cache(self, user_id: int) -> bool:
        """
        Invalidate all cached recommendations for a user

        Called when user has new interactions.

        Args:
            user_id: User ID

        Returns:
            True if successful, False otherwise
        """

        try:
            # Delete all algorithm caches for this user
            pattern = f"recs:user:{user_id}:*"
            keys = self.redis_client.keys(pattern)

            if keys:
                self.redis_client.delete(*keys)

            return True

        except Exception as e:
            print(f"Error invalidating user cache: {e}")
            return False

    def track_interaction(
        self, user_id: int, item_id: int, interaction_type: str, weight: float = 1.0
    ) -> bool:
        """
        Track a real-time interaction

        Stores interaction in Redis for fast access and batch processing.

        Args:
            user_id: User ID
            item_id: Item ID
            interaction_type: Type of interaction
            weight: Weight of interaction

        Returns:
            True if successful, False otherwise
        """

        try:
            # Store in sorted set with timestamp as score
            key = f"interactions:user:{user_id}"
            timestamp = datetime.utcnow().timestamp()

            interaction_data = json.dumps({
                "item_id": item_id,
                "interaction_type": interaction_type,
                "weight": weight,
                "timestamp": timestamp
            })

            # Add to sorted set
            self.redis_client.zadd(key, {interaction_data: timestamp})

            # Keep only last 1000 interactions per user
            self.redis_client.zremrangebyrank(key, 0, -1001)

            # Set expiry (30 days)
            self.redis_client.expire(key, 30 * 24 * 3600)

            # Invalidate user's cached recommendations
            self.invalidate_user_cache(user_id)

            return True

        except Exception as e:
            print(f"Error tracking interaction: {e}")
            return False

    def get_recent_interactions(
        self, user_id: int, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get recent interactions for a user from cache

        Args:
            user_id: User ID
            limit: Maximum number of interactions to return

        Returns:
            List of interaction dictionaries
        """

        try:
            key = f"interactions:user:{user_id}"

            # Get most recent interactions
            interactions = self.redis_client.zrevrange(key, 0, limit - 1)

            return [json.loads(interaction) for interaction in interactions]

        except Exception as e:
            print(f"Error getting recent interactions: {e}")
            return []

    def update_item_popularity(self, item_id: int, increment: float = 1.0) -> bool:
        """
        Update item popularity score in real-time

        Args:
            item_id: Item ID
            increment: Amount to increment popularity by

        Returns:
            True if successful, False otherwise
        """

        try:
            key = "item:popularity"
            self.redis_client.zincrby(key, increment, f"item:{item_id}")
            return True

        except Exception as e:
            print(f"Error updating item popularity: {e}")
            return False

    def get_trending_items(self, limit: int = 10, time_window: int = 3600) -> List[int]:
        """
        Get trending items based on recent interactions

        Args:
            limit: Number of items to return
            time_window: Time window in seconds (default: 1 hour)

        Returns:
            List of item IDs
        """

        try:
            key = "item:trending"
            cutoff_time = (datetime.utcnow() - timedelta(seconds=time_window)).timestamp()

            # Get items with recent activity
            trending = self.redis_client.zrevrangebyscore(
                key, '+inf', cutoff_time, start=0, num=limit
            )

            # Extract item IDs
            item_ids = [int(item.split(':')[1]) for item in trending if ':' in item]

            return item_ids

        except Exception as e:
            print(f"Error getting trending items: {e}")
            return []

    def record_trending_activity(self, item_id: int) -> bool:
        """
        Record activity for trending calculation

        Args:
            item_id: Item ID

        Returns:
            True if successful, False otherwise
        """

        try:
            key = "item:trending"
            timestamp = datetime.utcnow().timestamp()

            self.redis_client.zadd(key, {f"item:{item_id}": timestamp})

            # Clean up old entries (older than 24 hours)
            cutoff = (datetime.utcnow() - timedelta(hours=24)).timestamp()
            self.redis_client.zremrangebyscore(key, '-inf', cutoff)

            return True

        except Exception as e:
            print(f"Error recording trending activity: {e}")
            return False

    def _get_cache_key(self, user_id: int, algorithm: str) -> str:
        """Generate cache key for recommendations"""
        return f"recs:user:{user_id}:{algorithm}"

    def health_check(self) -> bool:
        """
        Check if Redis connection is healthy

        Returns:
            True if healthy, False otherwise
        """

        try:
            return self.redis_client.ping()
        except Exception:
            return False
