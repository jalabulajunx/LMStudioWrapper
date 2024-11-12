# tests/test_auth.py
import pytest
from fastapi import status
from app.auth.utils import verify_password, get_password_hash

def test_login_success(client, test_user):
    """Test successful login."""
    response = client.post(
        "/api/auth/token",
        json={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

def test_login_wrong_password(client, test_user):
    """Test login with wrong password."""
    response = client.post(
        "/api/auth/token",
        json={
            "username": "testuser",
            "password": "wrongpass"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_login_inactive_user(client, test_user, db_session):
    """Test login with inactive user."""
    test_user.is_active = False
    db_session.commit()
    
    response = client.post(
        "/api/auth/token",
        json={
            "username": "testuser",
            "password": "testpass123"
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_user(client, user_token):
    """Test getting current user info."""
    response = client.get("/api/auth/me", headers=user_token)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testuser"
    assert "email" in data
    assert not data["is_admin"]

def test_get_current_user_no_token(client):
    """Test getting current user without token."""
    response = client.get("/api/auth/me")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_current_admin(client, admin_token):
    """Test getting admin user info."""
    response = client.get("/api/auth/me", headers=admin_token)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "testadmin"
    assert data["is_admin"]

def test_password_hashing():
    """Test password hashing functionality."""
    password = "testpass123"
    hashed = get_password_hash(password)
    assert verify_password(password, hashed)
    assert not verify_password("wrongpass", hashed)