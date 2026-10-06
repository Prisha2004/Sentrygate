import os
import httpx
from typing import Dict, Any, List, Tuple, AsyncGenerator
from dotenv import load_dotenv

load_dotenv()

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip("\"' ")

# Primary model is configurable; fallbacks are tried in order.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACKS = [GEMINI_MODEL, "gemini-2.5-flash-lite", "gemini-2.0-flash"]
GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _redact(text: str) -> str:
    return text.replace(GEMINI_API_KEY, "***") if GEMINI_API_KEY else text


class UniversalRouter:
    def __init__(self):
        self.http_client = httpx.AsyncClient(timeout=45.0)

    def select_model(self, prompt: str, requested_model: str = "sentry-auto") -> Tuple[str, str]:
        if GEMINI_API_KEY:
            return GEMINI_MODEL, "gemini"
        return "gemma3:4b", "ollama"

    async def forward_request(self, model: str, messages: List[Dict[str, str]], stream: bool = False) -> Any:
        user_prompt = ""
        for m in reversed(messages):
            if m.get("role") == "user":
                user_prompt = m.get("content", "")
                break

        # 1. Google Gemini
        if GEMINI_API_KEY:
            headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
            payload = {"contents": [{"parts": [{"text": user_prompt}]}]}
            last_error = ""
            seen = set()
            for name in GEMINI_FALLBACKS:
                if name in seen:
                    continue
                seen.add(name)
                url = f"{GEMINI_BASE}/{name}:generateContent"
                try:
                    resp = await self.http_client.post(url, headers=headers, json=payload)
                    resp.raise_for_status()
                    answer = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
                    return {
                        "model": name,
                        "choices": [{"message": {"role": "assistant", "content": answer}}],
                    }
                except Exception as e:
                    last_error = f"{name}: {_redact(str(e))}"
                    continue
            return {
                "model": GEMINI_MODEL,
                "choices": [{"message": {"role": "assistant",
                                         "content": f"⚠️ Gemini Error: {last_error}"}}],
            }

        # 2. Local Ollama fallback
        url = f"{OLLAMA_BASE_URL}/chat/completions"
        payload = {"model": model, "messages": messages, "stream": stream}
        headers = {"Content-Type": "application/json"}
        try:
            if stream:
                return self._stream_response(url, headers, payload)
            resp = await self.http_client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {
                "model": model,
                "choices": [{"message": {"role": "assistant",
                                         "content": f"⚠️ Local Provider Error: {str(e)}"}}],
            }

    async def _stream_response(self, url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> AsyncGenerator[str, None]:
        async with self.http_client.stream("POST", url, headers=headers, json=payload) as response:
            async for line in response.aiter_lines():
                if line:
                    yield line