import json
import time
import uuid
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, StreamingResponse, JSONResponse
from pydantic import BaseModel

from cache import SemanticCache
from router import UniversalRouter
from auditor import SecurityAuditor
from dotenv import load_dotenv
load_dotenv()

app = FastAPI(title="SentryGate", version="0.1.0")


cache = SemanticCache()
router = UniversalRouter()
auditor = SecurityAuditor()

# In-memory session stats for the dashboard
stats = {
    "total_requests": 0,
    "cache_hits": 0,
    "total_cost_saved": 0.0,
    "total_latency_ms": 0.0
}

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: Optional[str] = "sentry-auto"
    messages: List[ChatMessage]
    stream: Optional[bool] = False
    tenant_id: Optional[str] = "default"
    user_role: Optional[str] = "developer"

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "SentryGate", "version": "0.1.0"}

@app.get("/api/stats")
def get_stats():
    avg_latency = round(stats["total_latency_ms"] / max(1, stats["total_requests"]), 2)
    hit_rate = round((stats["cache_hits"] / max(1, stats["total_requests"])) * 100, 1)
    return {
        "total_requests": stats["total_requests"],
        "cache_hits": stats["cache_hits"],
        "hit_rate_pct": hit_rate,
        "cost_saved_usd": round(stats["total_cost_saved"], 4),
        "avg_latency_ms": avg_latency
    }

@app.post("/api/cache/clear")
def clear_cache():
    global cache
    cache = SemanticCache()
    return {"status": "cleared"}

@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {"id": "sentry-auto", "object": "model", "owned_by": "sentrygate"},
            {"id": "gemma3:4b", "object": "model", "owned_by": "ollama"},
            {"id": "llama3:latest", "object": "model", "owned_by": "ollama"}
        ]
    }

@app.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, raw_req: Request):
    start_time = time.time()
    stats["total_requests"] += 1
    
    # Extract last user message
    user_prompt = ""
    for msg in reversed(req.messages):
        if msg.role == "user":
            user_prompt = msg.content
            break

    tenant_id = raw_req.headers.get("X-Tenant-ID", req.tenant_id or "default")
    user_role = raw_req.headers.get("X-User-Role", req.user_role or "developer")

    # 1. Check Semantic Cache
    hit, cached_response, cached_meta, cache_latency = cache.query(user_prompt, tenant_id=tenant_id)

    if hit and cached_response:
        stats["cache_hits"] += 1
        total_latency = cache_latency
        stats["total_latency_ms"] += total_latency
        
        dossier = auditor.generate_dossier(
            prompt=user_prompt,
            response_text=cached_response,
            cache_hit=True,
            latency_ms=total_latency,
            model_used=cached_meta.get("model_used", "cached"),
            tenant_id=tenant_id,
            user_role=user_role
        )
        stats["total_cost_saved"] += dossier["cost_saved_usd"]

        if req.stream:
            async def cached_stream():
                chunk_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
                chunk_data = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": dossier["model_used"],
                    "choices": [{"index": 0, "delta": {"content": cached_response}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(chunk_data)}\n\n"
                yield "data: [DONE]\n\n"

            headers = {
                "X-Sentry-Cache-Hit": "true",
                "X-Sentry-Latency-Ms": str(total_latency),
                "X-Sentry-Cost-Saved": str(dossier["cost_saved_usd"]),
                "X-Sentry-Dossier": json.dumps(dossier)
            }
            return StreamingResponse(cached_stream(), media_type="text/event-stream", headers=headers)
        else:
            return JSONResponse(
                content={
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": dossier["model_used"],
                    "choices": [{
                        "index": 0,
                        "message": {"role": "assistant", "content": cached_response},
                        "finish_reason": "stop"
                    }],
                    "sentry_dossier": dossier
                },
                headers={
                    "X-Sentry-Cache-Hit": "true",
                    "X-Sentry-Latency-Ms": str(total_latency),
                    "X-Sentry-Cost-Saved": str(dossier["cost_saved_usd"])
                }
            )

    # 2. Cache Miss: Route to Model
    selected_model, provider = router.select_model(user_prompt, req.model or "sentry-auto")
    message_dicts = [{"role": m.role, "content": m.content} for m in req.messages]

    if req.stream:
        stream_gen = await router.forward_request(model=selected_model, messages=message_dicts, stream=True)
        
        async def atomic_stream():
            collected_tokens = []
            async for line in stream_gen:
                yield f"{line}\n\n"
                if line.startswith("data: ") and not line.endswith("[DONE]"):
                    try:
                        parsed = json.loads(line[6:])
                        token = parsed["choices"][0]["delta"].get("content", "")
                        collected_tokens.append(token)
                    except Exception:
                        pass
            
            # Cache upon successful completion
            full_response = "".join(collected_tokens).strip()
            if full_response:
                cache.set(user_prompt, full_response, tenant_id=tenant_id, model_used=selected_model)

        return StreamingResponse(atomic_stream(), media_type="text/event-stream", headers={"X-Sentry-Cache-Hit": "false"})

    else:
        # Non-streaming model call
        raw_res = await router.forward_request(model=selected_model, messages=message_dicts, stream=False)
        total_latency = round((time.time() - start_time) * 1000, 2)
        stats["total_latency_ms"] += total_latency
        
        answer = raw_res["choices"][0]["message"]["content"]
        # Save to semantic cache for future requests
        cache.set(user_prompt, answer, tenant_id=tenant_id, model_used=selected_model)

        dossier = auditor.generate_dossier(
            prompt=user_prompt,
            response_text=answer,
            cache_hit=False,
            latency_ms=total_latency,
            model_used=selected_model,
            tenant_id=tenant_id,
            user_role=user_role
        )

        raw_res["sentry_dossier"] = dossier
        return JSONResponse(
            content=raw_res,
            headers={
                "X-Sentry-Cache-Hit": "false",
                "X-Sentry-Latency-Ms": str(total_latency),
                "X-Sentry-Model": selected_model
            }
        )

@app.get("/", response_class=HTMLResponse)
def index():
    try:
        with open("dashboard.html", "r") as f:
            return f.read()
    except FileNotFoundError:
        return "<h1>SentryGate API is Running.</h1><p>dashboard.html not found.</p>"
