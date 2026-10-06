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
        if GEMINI_API_KEY:
            return "gemini-1.5-flash", "gemini"
        return "gemma3:4b", "ollama"

    async def forward_request(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        user_prompt = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_prompt = m.get("content", "")
                break

        # 1. Native Google Gemini with official header (Fixes AQ. keys)
        if GEMINI_API_KEY:
            endpoints_to_try = [
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent",
                "https://generativelanguage.googleapis.com/v1/models/gemini-1.5-flash:generateContent",
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
            ]
            headers = {
                "x-goog-api-key": GEMINI_API_KEY,
                "Content-Type": "application/json"
            }
            gemini_payload = {
                "contents": [{"parts": [{"text": user_prompt}]}]
            }

            last_error = ""
            for url in endpoints_to_try:
                try:
                    resp = await self.http_client.post(url, headers=headers, json=gemini_payload)
                    resp.raise_for_status()
                    data = resp.json()
                    answer = data["candidates"][0]["content"]["parts"][0]["text"]
                    return {
                        "model": "gemini-1.5-flash",
                        "choices": [{
                            "message": {"role": "assistant", "content": answer}
                        }]
                    }
                except Exception as e:
                    last_error = str(e)
                    continue

            return {
                "model": "gemini-1.5-flash",
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"⚠️ Gemini Error: {last_error}"
                    }
                }]
            }

        # 2. Local Ollama Fallback
        url = f"{OLLAMA_BASE_URL}/chat/completions"
        payload = {"model": model, "messages": messages, "stream": stream}
        headers = {"Content-Type": "application/json"}

        try:
            if stream:
                return self._stream_response(url, headers, payload)
            else:
                resp = await self.http_client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            return {
                "model": model,
                "choices": [{
                    "message": {
                        "role": "assistant",
                        "content": f"⚠️ Local Provider Error: {str(e)}"
                    }
                }]
            }

    async def _stream_response(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        async with self.http_client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    yield line