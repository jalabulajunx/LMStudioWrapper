# tests/test_llm_service.py
import pytest
import aiohttp
from app.services.llm_service import LLMService, LMStudioConnectionError

@pytest.mark.asyncio
async def test_check_server_status():
    """Test LM Studio server status check."""
    service = LLMService()
    # Test with mock server
    async with aiohttp.ClientSession() as session:
        async def mock_get(*args, **kwargs):
            class MockResponse:
                status = 200
            return MockResponse()
        
        session.get = mock_get
        status = await service.check_server_status()
        assert status is True

def test_format_messages():
    """Test conversation history formatting."""
    service = LLMService()
    history = [
        {"content": "Hello", "response": "Hi there!"},
        {"content": "How are you?", "response": "I'm good!"}
    ]
    new_message = "What's the weather?"
    
    messages = service.format_messages(history, new_message)
    
    assert len(messages) == 6  # system + 4 history + 1 new
    assert messages[0]["role"] == "system"
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"] == new_message

def test_estimate_token_length():
    """Test token length estimation."""
    service = LLMService()
    messages = [
        {"role": "user", "content": "Hello there!"},
        {"role": "assistant", "content": "Hi! How can I help you?"}
    ]
    
    estimated_tokens = service.estimate_token_length(messages)
    assert estimated_tokens > 0
    # Rough check: English text averages ~4 chars per token
    total_chars = sum(len(msg["content"]) for msg in messages)
    assert estimated_tokens == total_chars // 4

def test_adjust_context_for_length():
    """Test context length adjustment."""
    service = LLMService()
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi!"},
        {"role": "user", "content": "How are you?"},
        {"role": "assistant", "content": "I'm good!"},
        {"role": "user", "content": "New message"}
    ]
    
    # Test with very small context window
    adjusted = service.adjust_context_for_length(messages, max_context_length=20)
    assert len(adjusted) < len(messages)
    # Verify system message and latest user message are kept
    assert adjusted[0]["role"] == "system"
    assert adjusted[-1]["content"] == "New message"

@pytest.mark.asyncio
async def test_generate_stream():
    """Test message generation with streaming."""
    service = LLMService()
    history = [
        {"content": "Hello", "response": "Hi there!"}
    ]
    
    async def mock_stream():
        tokens = ["This ", "is ", "a ", "test ", "response."]
        for token in tokens:
            yield token
    
    # Replace actual API call with mock
    service.generate_stream = mock_stream
    
    full_response = ""
    async for token in service.generate_stream("Test message", history):
        full_response += token
    
    assert full_response == "This is a test response."

@pytest.mark.asyncio
async def test_generate_stream_error():
    """Test error handling in stream generation."""
    service = LLMService()
    
    # Mock a failed API call
    async def mock_failed_stream():
        raise LMStudioConnectionError("Connection failed")
    
    service.generate_stream = mock_failed_stream
    
    with pytest.raises(LMStudioConnectionError):
        async for _ in service.generate_stream("Test message"):
            pass