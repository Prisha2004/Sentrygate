import os
import httpx
from typing import Dict, Any, List, Tuple, AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip("\"' ")

class UniversalRouter:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=45.0)

    def select_model(self, prompt: str, requested_model: str = "sentry-auto") -> Tuple[str, str]:
        # On Cloud (Render) where GEMINI_API_KEY exists, always route to Gemini 1.5 Flash
        if GEMINI_API_KEY:
            return "gemini-1.5-flash", "gemini"
        
        # On Local Laptop where Ollama is running
        return "gemma3:4b", "ollama"

    async def forward_request(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream
        }

        # Route to Google Gemini Cloud
        if GEMINI_API_KEY:
            url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
            headers = {
                "Authorization": f"Bearer {GEMINI_API_KEY}",
                "Content-Type": "application/json"
            }
        else:
            # Route to Local Ollama
            url = f"{OLLAMA_BASE_URL}/chat/completions"
            headers = {"Content-Type": "application/json"}

        try:
            if stream:
                return self._stream_response(url, headers, payload)
            else:
                resp = await self.http_client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            # Graceful error capture instead of crashing with 500
            return {
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"⚠️ SentryGate Routing Notice: Error contacting provider ({model}): {str(e)}"
                    }
                }]
            }

    async def _stream_response(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        async with self.http_client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    yield line