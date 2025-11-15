"""Tests for API endpoints"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.utils.database import get_db


@pytest.fixture
def test_db():
    """Create a test database"""

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)

    TestingSessionLocal = sessionmaker(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    yield

    app.dependency_overrides.clear()


@pytest.fixture
def client(test_db):
    """Create a test client"""
    return TestClient(app)


def test_root_endpoint(client):
    """Test root endpoint"""

    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_create_user(client):
    """Test creating a user"""

    response = client.post(
        "/api/v1/users/",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "preferences": {}
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data


def test_create_duplicate_user(client):
    """Test creating a duplicate user fails"""

    # Create first user
    client.post(
        "/api/v1/users/",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "preferences": {}
        }
    )

    # Try to create duplicate
    response = client.post(
        "/api/v1/users/",
        json={
            "username": "testuser",
            "email": "test2@example.com",
            "preferences": {}
        }
    )

    assert response.status_code == 400


def test_list_users(client):
    """Test listing users"""

    # Create a user first
    client.post(
        "/api/v1/users/",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "preferences": {}
        }
    )

    response = client.get("/api/v1/users/")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
    assert len(response.json()) == 1


def test_create_item(client):
    """Test creating an item"""

    response = client.post(
        "/api/v1/items/",
        json={
            "title": "Test Item",
            "description": "A test item",
            "category": "test",
            "tags": ["tag1", "tag2"],
            "features": {}
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Item"
    assert data["category"] == "test"


def test_create_interaction(client):
    """Test creating an interaction"""

    # Create user and item first
    user_response = client.post(
        "/api/v1/users/",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "preferences": {}
        }
    )
    user_id = user_response.json()["id"]

    item_response = client.post(
        "/api/v1/items/",
        json={
            "title": "Test Item",
            "description": "A test item",
            "category": "test",
            "tags": [],
            "features": {}
        }
    )
    item_id = item_response.json()["id"]

    # Create interaction
    response = client.post(
        "/api/v1/interactions/",
        json={
            "user_id": user_id,
            "item_id": item_id,
            "interaction_type": "view",
            "rating": 5.0,
            "weight": 1.0
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["user_id"] == user_id
    assert data["item_id"] == item_id
    assert data["interaction_type"] == "view"


def test_get_recommendations_no_interactions(client):
    """Test getting recommendations for user with no interactions"""

    # Create a user
    user_response = client.post(
        "/api/v1/users/",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "preferences": {}
        }
    )
    user_id = user_response.json()["id"]

    # Get recommendations
    response = client.get(f"/api/v1/recommendations/user/{user_id}")

    # Should succeed but return empty or popular items
    assert response.status_code == 200
    data = response.json()
    assert "recommendations" in data
