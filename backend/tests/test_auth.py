"""
PoCP AI Commons — Authentication System Tests
===============================================
Comprehensive test suite covering registration, login, token rotation,
logout, and protected route access control.

Run with:
    pytest tests/test_auth.py
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models.entity import Entity, EntityType

# Setup test SQLite database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test_pocp.db"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db():
    """Create a clean database session for each test."""
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db):
    """Create a test client that overrides get_db dependency."""

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Test Registration
# ---------------------------------------------------------------------------


def test_register_account_success(client):
    """Test registering a new account successfully."""
    payload = {
        "email": "test@pocp.dev",
        "password": "strongpassword123",
        "name": "Test Contributor",
        "description": "I am a tester",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["account"]["email"] == "test@pocp.dev"
    assert data["account"]["is_active"] is True
    assert data["account"]["is_superuser"] is False


def test_register_duplicate_email(client):
    """Test registration fails with a duplicate email."""
    payload = {
        "email": "duplicate@pocp.dev",
        "password": "strongpassword123",
        "name": "First User",
    }
    # First registration
    client.post("/api/v1/auth/register", json=payload)

    # Second registration
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


# ---------------------------------------------------------------------------
# Test Login
# ---------------------------------------------------------------------------


def test_login_success(client):
    """Test login with correct credentials."""
    # Register first
    reg_payload = {
        "email": "login@pocp.dev",
        "password": "loginpassword123",
        "name": "Login User",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Login
    login_data = {"username": "login@pocp.dev", "password": "loginpassword123"}
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_login_invalid_credentials(client):
    """Test login fails with incorrect password."""
    reg_payload = {
        "email": "login@pocp.dev",
        "password": "loginpassword123",
        "name": "Login User",
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Wrong password
    login_data = {"username": "login@pocp.dev", "password": "wrongpassword"}
    response = client.post("/api/v1/auth/login", data=login_data)
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Test Token Refresh
# ---------------------------------------------------------------------------


def test_refresh_token_rotation(client):
    """Test exchanging a refresh token for a new pair (rotation)."""
    reg_payload = {
        "email": "refresh@pocp.dev",
        "password": "refreshpassword123",
        "name": "Refresh User",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    refresh_token = reg_resp.json()["refresh_token"]

    # Refresh
    response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200

    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token  # Must be a new token (rotated)

    # Reusing the old refresh token must fail (revoked)
    reuse_response = client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reuse_response.status_code == 401


# ---------------------------------------------------------------------------
# Test Protected Routes & Access Control
# ---------------------------------------------------------------------------


def test_get_profile_authenticated(client):
    """Test accessing the profile route with a valid token."""
    reg_payload = {
        "email": "profile@pocp.dev",
        "password": "profilepassword123",
        "name": "Profile User",
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_resp.json()["access_token"]

    # Access /me
    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200

    profile = response.json()
    assert profile["email"] == "profile@pocp.dev"
    assert profile["name"] == "Profile User"
    assert profile["ai_credits"] == 100.0  # Verification of registration credits


def test_protected_routes_unauthorized(client):
    """Test that protected routes block requests without tokens."""
    # Try public endpoint (should work)
    assert client.get("/health").status_code == 200

    # Try protected endpoint (should fail)
    assert client.get("/api/v1/auth/me").status_code == 401
    assert client.post("/api/v1/protected/tasks", json={}).status_code == 401
