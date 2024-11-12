# tests/test_settings.py
import pytest
from fastapi import status

def test_list_models(client, user_token):
    """Test listing available LM Studio models."""
    response = client.get("/api/settings/models", headers=user_token)
    assert response.status_code == status.HTTP_200_OK
    models = response.json()
    assert isinstance(models, list)
    # At least one model should be available
    assert len(models) > 0

def test_list_models_unauthorized(client):
    """Test listing models without authentication."""
    response = client.get("/api/settings/models")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_list_models_server_error(client, user_token, monkeypatch):
    """Test handling LM Studio server errors."""
    async def mock_error_request(*args, **kwargs):
        class MockResponse:
            status = 500
            async def json(self):
                return {"error": "Server error"}
        return MockResponse()

    # Mock the aiohttp client session
    monkeypatch.setattr("aiohttp.ClientSession.get", mock_error_request)
    
    response = client.get("/api/settings/models", headers=user_token)
    assert response.status_code == status.HTTP_502_BAD_GATEWAY