import json
import aiohttp
import asyncio
from typing import AsyncGenerator, Optional, List, Dict
from ..config import settings
import logging

logger = logging.getLogger(__name__)

class LMStudioConnectionError(Exception):
    """Raised when connection to LM Studio fails"""
    pass

class LLMService:
    def __init__(self):
        self.base_url = settings.LM_STUDIO_URL
        self.api_key = settings.LM_STUDIO_KEY
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.max_retries = 3
        self.retry_delay = 2  # seconds
        
        # LM Studio context parameters
        self.default_params = {
            "max_tokens": 2000,          # Maximum length of the response
            "context_length": 4096,      # Maximum context window length
            "temperature": 0.7,          # Randomness in generation
            "top_p": 0.9,               # Nucleus sampling parameter
            "repeat_penalty": 1.1,       # Penalty for repeating tokens
            "top_k": 40,                # Top-k sampling parameter
            "stop": [],                 # Stop sequences
            "frequency_penalty": 0.0,    # Penalty for token frequency
            "presence_penalty": 0.0      # Penalty for token presence
        }

    async def check_server_status(self) -> bool:
        """Check if LM Studio server is available"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=self.headers,
                    timeout=5
                ) as response:
                    return response.status == 200
        except Exception as e:
            logger.error(f"LM Studio server check failed: {str(e)}")
            return False

    def format_messages(self, conversation_history: List[dict], new_message: str) -> List[dict]:
        """Format conversation history and new message into LM Studio message format"""
        messages = []
        
        # Add system message to establish context
        messages.append({
            "role": "user",
            "content": "You are a helpful assistant. Please respond based on the entire conversation context."
        })
        
        # Add conversation history
        for msg in conversation_history:
            if msg.get('content'):
                messages.append({
                    "role": "user",
                    "content": msg['content']
                })
            if msg.get('response'):
                messages.append({
                    "role": "assistant",
                    "content": msg['response']
                })
        
        # Add new message
        messages.append({
            "role": "user",
            "content": new_message
        })
        
        return messages

    def estimate_token_length(self, messages: List[dict]) -> int:
        """
        Roughly estimate token length of messages.
        This is a very rough approximation: ~4 chars per token for English text.
        """
        total_chars = sum(len(msg["content"]) for msg in messages)
        estimated_tokens = total_chars // 4
        return estimated_tokens

    def adjust_context_for_length(self, messages: List[dict], max_context_length: int = None) -> List[dict]:
        """
        Adjust context by removing older messages if estimated length exceeds max context length.
        Keeps system message and most recent messages.
        """
        if not max_context_length:
            max_context_length = self.default_params["context_length"]

        # Always keep system message and latest user message
        if len(messages) <= 2:
            return messages

        system_message = messages[0]
        latest_message = messages[-1]
        history_messages = messages[1:-1]

        while (self.estimate_token_length(messages) > max_context_length and len(history_messages) > 0):
            # Remove oldest pair of messages (user + assistant)
            if len(history_messages) >= 2:
                history_messages = history_messages[2:]
            else:
                history_messages = []

            messages = [system_message] + history_messages + [latest_message]

        return messages

    async def generate_stream(
        self, 
        prompt: str, 
        conversation_history: Optional[List[dict]] = None,
        params: Optional[Dict] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generates streaming response from LM Studio with conversation history context
        and configurable parameters.
        """
        messages = self.format_messages(conversation_history or [], prompt)
        
        # Merge default params with any provided params
        generation_params = self.default_params.copy()
        if params:
            generation_params.update(params)

        # Adjust context if needed
        messages = self.adjust_context_for_length(
            messages, 
            generation_params.get("context_length")
        )
        
        estimated_tokens = self.estimate_token_length(messages)
        logger.debug(f"Estimated context length: {estimated_tokens} tokens")
        
        for attempt in range(self.max_retries):
            try:
                if not await self.check_server_status():
                    raise LMStudioConnectionError("LM Studio server is not available")

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json={
                            "messages": messages,
                            "model": "local-model",
                            "stream": True,
                            **generation_params
                        },
                        timeout=aiohttp.ClientTimeout(total=300)  # 5 minutes timeout
                    ) as response:
                        if response.status != 200:
                            error_text = await response.text()
                            raise LMStudioConnectionError(f"LM Studio returned status {response.status}: {error_text}")

                        async for line in response.content:
                            if line:
                                text = line.decode('utf-8').strip()
                                if text.startswith('data: '):
                                    text = text[6:]
                                    if text == '[DONE]':
                                        break
                                    try:
                                        data = json.loads(text)
                                        if content := data.get('choices', [{}])[0].get('delta', {}).get('content'):
                                            yield content
                                    except json.JSONDecodeError:
                                        continue
                        return

            except (aiohttp.ClientError, LMStudioConnectionError) as e:
                logger.error(f"Attempt {attempt + 1} failed: {str(e)}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                else:
                    yield f"\n\nError: Unable to connect to LM Studio after {self.max_retries} attempts. Please ensure the server is running and try again."
                    return