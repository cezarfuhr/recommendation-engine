"""Tests for Collaborative Filtering Service"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import numpy as np

from app.models.base import Base
from app.models import User, Item, Interaction
from app.services.collaborative_filtering import CollaborativeFilteringService


@pytest.fixture
def db_session():
    """Create a test database session"""

    # Use in-memory SQLite for tests
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)
    session = TestingSessionLocal()

    yield session

    session.close()


@pytest.fixture
def sample_data(db_session):
    """Create sample data for testing"""

    # Create users
    users = [
        User(id=1, username="user1", email="user1@example.com"),
        User(id=2, username="user2", email="user2@example.com"),
        User(id=3, username="user3", email="user3@example.com"),
    ]
    db_session.add_all(users)

    # Create items
    items = [
        Item(id=1, title="Item 1", category="books"),
        Item(id=2, title="Item 2", category="books"),
        Item(id=3, title="Item 3", category="movies"),
        Item(id=4, title="Item 4", category="movies"),
    ]
    db_session.add_all(items)

    # Create interactions
    interactions = [
        Interaction(user_id=1, item_id=1, interaction_type="view", rating=5.0, weight=1.0),
        Interaction(user_id=1, item_id=2, interaction_type="view", rating=4.0, weight=1.0),
        Interaction(user_id=2, item_id=1, interaction_type="view", rating=5.0, weight=1.0),
        Interaction(user_id=2, item_id=3, interaction_type="view", rating=4.0, weight=1.0),
        Interaction(user_id=3, item_id=2, interaction_type="view", rating=3.0, weight=1.0),
        Interaction(user_id=3, item_id=4, interaction_type="view", rating=5.0, weight=1.0),
    ]
    db_session.add_all(interactions)

    db_session.commit()

    return users, items, interactions


def test_build_user_item_matrix(db_session, sample_data):
    """Test building user-item matrix"""

    service = CollaborativeFilteringService(db_session)
    matrix = service.build_user_item_matrix()

    assert matrix is not None
    assert matrix.shape == (3, 4)  # 3 users, 4 items
    assert matrix[0, 0] == 5.0  # User 1, Item 1


def test_compute_user_similarity(db_session, sample_data):
    """Test computing user similarity matrix"""

    service = CollaborativeFilteringService(db_session)
    similarity_matrix = service.compute_user_similarity()

    assert similarity_matrix is not None
    assert similarity_matrix.shape == (3, 3)
    # Diagonal should be 0 (users not similar to themselves)
    assert similarity_matrix[0, 0] == 0


def test_get_user_based_recommendations(db_session, sample_data):
    """Test user-based collaborative filtering recommendations"""

    service = CollaborativeFilteringService(db_session)
    recommendations = service.get_user_based_recommendations(user_id=1, top_n=2)

    assert isinstance(recommendations, list)
    assert len(recommendations) <= 2

    # Recommendations should be tuples of (item_id, score)
    if recommendations:
        assert isinstance(recommendations[0], tuple)
        assert isinstance(recommendations[0][0], (int, np.integer))
        assert isinstance(recommendations[0][1], (float, np.floating))


def test_get_item_based_recommendations(db_session, sample_data):
    """Test item-based collaborative filtering recommendations"""

    service = CollaborativeFilteringService(db_session)
    recommendations = service.get_item_based_recommendations(user_id=1, top_n=2)

    assert isinstance(recommendations, list)
    assert len(recommendations) <= 2


def test_exclude_interacted_items(db_session, sample_data):
    """Test that recommendations exclude items user has already interacted with"""

    service = CollaborativeFilteringService(db_session)
    recommendations = service.get_recommendations(user_id=1, top_n=10, exclude_interacted=True)

    # User 1 has interacted with items 1 and 2
    recommended_item_ids = [item_id for item_id, _ in recommendations]

    assert 1 not in recommended_item_ids
    assert 2 not in recommended_item_ids
