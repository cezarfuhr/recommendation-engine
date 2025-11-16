"""Tests for Feature Store"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

from app.models.base import Base
from app.models import User, Item, Interaction
from app.services.feature_store import FeatureStore


@pytest.fixture
def db_session():
    """Create a test database session"""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()


@pytest.fixture
def sample_data(db_session):
    """Create sample data for testing"""

    # Create user
    user = User(id=1, username="testuser", email="test@example.com", preferences={"age": 25})
    db_session.add(user)

    # Create items
    items = [
        Item(id=1, title="Item 1", category="books", tags=["fiction", "adventure"]),
        Item(id=2, title="Item 2", category="movies", tags=["action", "thriller"]),
    ]
    db_session.add_all(items)

    # Create interactions
    interactions = [
        Interaction(user_id=1, item_id=1, interaction_type="view", rating=5.0, weight=1.0),
        Interaction(user_id=1, item_id=2, interaction_type="purchase", rating=4.0, weight=2.0),
    ]
    db_session.add_all(interactions)

    db_session.commit()

    return user, items, interactions


def test_get_user_features(db_session, sample_data):
    """Test getting user features"""

    user, items, interactions = sample_data
    feature_store = FeatureStore(db_session)

    features = feature_store.get_user_features(user.id, use_cache=False)

    assert features["user_id"] == user.id
    assert features["total_interactions"] == 2
    assert "avg_rating" in features
    assert "favorite_categories" in features
    assert "activity_score" in features
    assert "recency_score" in features


def test_get_item_features(db_session, sample_data):
    """Test getting item features"""

    user, items, interactions = sample_data
    feature_store = FeatureStore(db_session)

    features = feature_store.get_item_features(items[0].id, use_cache=False)

    assert features["item_id"] == items[0].id
    assert features["title"] == items[0].title
    assert features["category"] == items[0].category
    assert features["tags"] == items[0].tags
    assert "total_interactions" in features
    assert "avg_rating" in features


def test_get_user_item_features(db_session, sample_data):
    """Test getting user-item contextual features"""

    user, items, interactions = sample_data
    feature_store = FeatureStore(db_session)

    features = feature_store.get_user_item_features(user.id, items[0].id, use_cache=False)

    assert features["user_id"] == user.id
    assert features["item_id"] == items[0].id
    assert "has_interacted" in features
    assert "category_match" in features


def test_favorite_categories(db_session, sample_data):
    """Test computing favorite categories"""

    user, items, interactions = sample_data
    feature_store = FeatureStore(db_session)

    favorite_categories = feature_store._compute_favorite_categories(user.id, top_n=2)

    assert isinstance(favorite_categories, list)
    # User interacted with books and movies
    assert len(favorite_categories) <= 2


def test_activity_score(db_session, sample_data):
    """Test computing activity score"""

    user, items, interactions = sample_data
    feature_store = FeatureStore(db_session)

    activity_score = feature_store._compute_activity_score(interactions)

    assert isinstance(activity_score, float)
    assert 0.0 <= activity_score <= 1.0


def test_recency_score(db_session, sample_data):
    """Test computing recency score"""

    user, items, interactions = sample_data
    feature_store = FeatureStore(db_session)

    recency_score = feature_store._compute_recency_score(interactions)

    assert isinstance(recency_score, float)
    assert 0.0 <= recency_score <= 1.0


def test_cache_invalidation(db_session, sample_data):
    """Test feature cache invalidation"""

    user, items, interactions = sample_data
    feature_store = FeatureStore(db_session)

    # Get features (will be cached)
    features1 = feature_store.get_user_features(user.id, use_cache=True)

    # Invalidate cache
    feature_store.invalidate_user_features(user.id)

    # Get features again (should recompute)
    features2 = feature_store.get_user_features(user.id, use_cache=True)

    # Both should have same values but different computed_at
    assert features1["user_id"] == features2["user_id"]
