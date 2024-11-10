import json
import aiohttp
import asyncio
from typing import AsyncGenerator, Optional
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

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """
        Generates streaming response from LM Studio with retry logic
        """
        for attempt in range(self.max_retries):
            try:
                if not await self.check_server_status():
                    raise LMStudioConnectionError("LM Studio server is not available")

                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=self.headers,
                        json={
                            "messages": [{"role": "user", "content": prompt}],
                            "model": "local-model",
                            "stream": True,
                            "temperature": 0.7,
                            "max_tokens": 2000
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
