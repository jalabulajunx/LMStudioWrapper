# tests/test_admin.py
import pytest
from fastapi import status

def test_list_users(client, admin_token, test_user):
    """Test listing users as admin."""
    response = client.get("/api/admin/users", headers=admin_token)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "items" in data
    assert len(data["items"]) > 0
    assert data["total"] > 0

def test_create_user(client, admin_token):
    """Test creating a new user as admin."""
    response = client.post(
        "/api/admin/users",
        headers=admin_token,
        json={
            "username": "newuser",
            "email": "new@example.com",
            "full_name": "New User",
            "password": "newpass123",
            "is_active": True,
            "roles": ["user"],
            "tasks": ["general"]
        }
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "new@example.com"

def test_update_user(client, admin_token, test_user):
    """Test updating a user as admin."""
    response = client.put(
        f"/api/admin/users/{test_user.id}",
        headers=admin_token,
        json={
            "full_name": "Updated Name",
            "is_active": True
        }
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["full_name"] == "Updated Name"

def test_delete_user(client, admin_token, test_user):
    """Test deleting a user as admin."""
    response = client.delete(
        f"/api/admin/users/{test_user.id}",
        headers=admin_token
    )
    assert response.status_code == status.HTTP_200_OK

def test_non_admin_access(client, user_token):
    """Test accessing admin endpoints as non-admin."""
    response = client.get("/api/admin/users", headers=user_token)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_list_roles(client, admin_token):
    """Test listing available roles."""
    response = client.get("/api/admin/roles", headers=admin_token)
    assert response.status_code == status.HTTP_200_OK
    roles = response.json()
    assert any(role["name"] == "admin" for role in roles)
    assert any(role["name"] == "user" for role in roles)

def test_list_tasks(client, admin_token):
    """Test listing available tasks."""
    response = client.get("/api/admin/tasks", headers=admin_token)
    assert response.status_code == status.HTTP_200_OK
    tasks = response.json()
    assert any(task["name"] == "general" for task in tasks)
    assert any(task["name"] == "music" for task in tasks)

def test_user_pagination(client, admin_token, db_session):
    """Test user list pagination."""
    # Create multiple test users
    for i in range(15):  # Create enough users to test pagination
        response = client.post(
            "/api/admin/users",
            headers=admin_token,
            json={
                "username": f"testuser{i}",
                "email": f"test{i}@example.com",
                "full_name": f"Test User {i}",
                "password": "testpass123",
                "is_active": True,
                "roles": ["user"],
                "tasks": ["general"]
            }
        )
        assert response.status_code == status.HTTP_200_OK

    # Test first page
    response = client.get(
        "/api/admin/users?page=1&page_size=10",
        headers=admin_token
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["total_pages"] > 1

    # Test second page
    response = client.get(
        "/api/admin/users?page=2&page_size=10",
        headers=admin_token
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) > 0
    assert data["page"] == 2

def test_user_search(client, admin_token, test_user):
    """Test user search functionality."""
    response = client.get(
        f"/api/admin/users?search={test_user.username}",
        headers=admin_token
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["username"] == test_user.username

def test_admin_cannot_delete_self(client, admin_token, test_admin):
    """Test that admin cannot delete their own account."""
    response = client.delete(
        f"/api/admin/users/{test_admin.id}",
        headers=admin_token
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_invalid_role_assignment(client, admin_token, test_user):
    """Test assigning invalid roles."""
    response = client.put(
        f"/api/admin/users/{test_user.id}",
        headers=admin_token,
        json={
            "roles": ["invalid_role"]
        }
    )
    assert response.status_code == status.HTTP_400_BAD_REQUEST