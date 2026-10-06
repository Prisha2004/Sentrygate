import os
import httpx
from typing import Dict, Any, List, Tuple, AsyncGenerator
from dotenv import load_dotenv

# Load GEMINI_API_KEY from .env
load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

REASONING_KEYWORDS = {"explain", "prove", "architect", "debug", "compare", "analyze", "why", "code", "optimize", "calculate"}

class UniversalRouter:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=60.0)

    def select_model(self, prompt: str, requested_model: str = "sentry-auto") -> Tuple[str, str]:
        # If Gemini key is set, use Gemini 1.5 Flash (sub-second free tier)
        if GEMINI_API_KEY and GEMINI_API_KEY.startswith("AIzaSy"):
            return "gemini-1.5-flash", "gemini"
        
        # Fallback to local Ollama on Mac
        words = set(prompt.lower().split())
        if len(words) > 25 or words.intersection(REASONING_KEYWORDS):
            return "llama3:latest", "ollama"
        else:
            return "gemma3:4b", "ollama"

    async def forward_request(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }

        # Check if routing to Google Gemini or Local Ollama
        if GEMINI_API_KEY and model.startswith("gemini"):
            url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            headers = {
                "Authorization": f"Bearer {GEMINI_API_KEY}",
                "Content-Type": "application/json"
            }
        else:
            url = f"{OLLAMA_BASE_URL}/chat/completions"
            headers = {"Content-Type": "application/json"}

        if stream:
            return self._stream_response(url, headers, payload)
        else:
            resp = await self.http_client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()

    async def _stream_response(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        async with self.http_client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    yield line