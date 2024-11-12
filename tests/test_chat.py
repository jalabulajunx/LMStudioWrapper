# tests/test_chat.py
import pytest
from fastapi import status
import json

def test_create_conversation(client, user_token):
    """Test creating a new conversation."""
    response = client.post("/api/conversations", headers=user_token)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "id" in data
    assert "title" in data
    assert data["title"] == "New Conversation"

def test_list_conversations(client, user_token, test_conversation):
    """Test listing user conversations."""
    response = client.get("/api/conversations", headers=user_token)
    assert response.status_code == status.HTTP_200_OK
    conversations = response.json()
    assert len(conversations) > 0
    assert conversations[0]["id"] == test_conversation.id
    assert conversations[0]["title"] == test_conversation.title

def test_get_conversation(client, user_token, test_conversation):
    """Test getting a specific conversation."""
    response = client.get(
        f"/api/conversations/{test_conversation.id}",
        headers=user_token
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["conversation"]["id"] == test_conversation.id
    assert len(data["messages"]) == 2

def test_delete_conversation(client, user_token, test_conversation):
    """Test deleting a conversation."""
    response = client.delete(
        f"/api/conversations/{test_conversation.id}",
        headers=user_token
    )
    assert response.status_code == status.HTTP_200_OK
    
    # Verify deletion
    response = client.get(
        f"/api/conversations/{test_conversation.id}",
        headers=user_token
    )
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_update_conversation_title(client, user_token, test_conversation):
    """Test updating conversation title."""
    new_title = "Updated Title"
    response = client.put(
        f"/api/conversations/{test_conversation.id}",
        headers=user_token,
        json={"title": new_title}
    )
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["title"] == new_title

@pytest.mark.asyncio
async def test_chat_message_streaming(client, user_token, test_conversation, mock_llm_service):
    """Test streaming chat messages."""
    response = client.post(
        "/api/chat",
        headers=user_token,
        json={
            "message": "Hello",
            "conversation_id": test_conversation.id
        },
        stream=True
    )
    assert response.status_code == status.HTTP_200_OK
    
    full_response = ""
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if "token" in data:
                    full_response += data["token"]
    
    assert "test response" in full_response

def test_chat_unauthorized(client, test_conversation):
    """Test chat without authentication."""
    response = client.post(
        "/api/chat",
        json={
            "message": "Hello",
            "conversation_id": test_conversation.id
        }
    )
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_chat_invalid_conversation(client, user_token):
    """Test chat with invalid conversation ID."""
    response = client.post(
        "/api/chat",
        headers=user_token,
        json={
            "message": "Hello",
            "conversation_id": "invalid-id"
        }
    )
    assert response.status_code == status.HTTP_200_OK  # Creates new conversation

@pytest.mark.asyncio
async def test_chat_llm_error(client, user_token, test_conversation, mock_llm_service_error):
    """Test chat with LLM service error."""
    response = client.post(
        "/api/chat",
        headers=user_token,
        json={
            "message": "Hello",
            "conversation_id": test_conversation.id
        },
        stream=True
    )
    assert response.status_code == status.HTTP_200_OK
    
    error_found = False
    for line in response.iter_lines():
        if line:
            line = line.decode('utf-8')
            if line.startswith("data: "):
                data = json.loads(line[6:])
                if "error" in data:
                    error_found = True
                    break
    
    assert error_found