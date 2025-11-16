"""Tests for Authentication"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.models.base import Base
from app.utils.database import get_db
from app.utils.auth import create_access_token, verify_password, get_password_hash


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


def test_register_user(client):
    """Test user registration"""

    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "preferences": {}
        }
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert "id" in data
    # Password should not be in response
    assert "password" not in data


def test_register_duplicate_username(client):
    """Test registering with duplicate username"""

    # Create first user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "preferences": {}
        }
    )

    # Try to create user with same username
    response = client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "other@example.com",
            "password": "testpass123",
            "preferences": {}
        }
    )

    assert response.status_code == 400
    assert "Username already exists" in response.json()["detail"]


def test_login(client):
    """Test user login"""

    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "preferences": {}
        }
    )

    # Login
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpass123"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Test login with invalid credentials"""

    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "preferences": {}
        }
    )

    # Try to login with wrong password
    response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpass"
        }
    )

    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


def test_get_current_user(client):
    """Test getting current user with token"""

    # Register user
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "preferences": {}
        }
    )

    # Login to get token
    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpass123"
        }
    )

    token = login_response.json()["access_token"]

    # Get current user
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


def test_get_current_user_invalid_token(client):
    """Test getting current user with invalid token"""

    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalid_token"}
    )

    assert response.status_code == 401


def test_refresh_token(client):
    """Test refreshing access token"""

    # Register and login
    client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpass123",
            "preferences": {}
        }
    )

    login_response = client.post(
        "/api/v1/auth/login",
        json={
            "email": "test@example.com",
            "password": "testpass123"
        }
    )

    refresh_token = login_response.json()["refresh_token"]

    # Refresh token
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


def test_password_hashing():
    """Test password hashing and verification"""

    password = "testpassword123"

    # Hash password
    hashed = get_password_hash(password)

    # Verify correct password
    assert verify_password(password, hashed) is True

    # Verify incorrect password
    assert verify_password("wrongpassword", hashed) is False


def test_token_creation():
    """Test JWT token creation and decoding"""

    from app.utils.auth import decode_token

    user_id = 123
    token = create_access_token(data={"sub": user_id})

    # Decode token
    payload = decode_token(token)

    assert payload["sub"] == user_id
    assert payload["type"] == "access"
    assert "exp" in payload
