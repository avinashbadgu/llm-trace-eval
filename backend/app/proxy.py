"""
LLM Proxy — forwards requests to OpenAI (or any OpenAI-compatible API),
captures (prompt, response, latency, tokens), persists a Trace, and enqueues
an evaluation job in the background.
"""
from __future__ import annotations

import os
import time
import uuid
from typing import Any

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal
from .models import Trace
from .schemas import _PRICING

router = APIRouter(prefix="/proxy", tags=["proxy"])

UPSTREAM_BASE = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


async def _persist_and_enqueue(payload: dict[str, Any], result: dict[str, Any], latency_ms: float) -> None:
    model = result.get("model", payload.get("model", "unknown"))
    usage = result.get("usage", {})
    prompt_tokens: int = usage.get("prompt_tokens", 0)
    completion_tokens: int = usage.get("completion_tokens", 0)

    rates = _PRICING.get(model, (0.000001, 0.000002))
    cost_usd = rates[0] * prompt_tokens + rates[1] * completion_tokens

    choices = result.get("choices", [])
    response_text = ""
    if choices:
        msg = choices[0].get("message", {})
        response_text = msg.get("content", "") or ""

    messages = payload.get("messages", [])
    prompt_text = "\n".join(m.get("content", "") for m in messages if isinstance(m.get("content"), str))
    question = next(
        (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
        prompt_text,
    )

    trace = Trace(
        id=uuid.uuid4(),
        model=model,
        prompt=prompt_text,
        response=response_text,
        question=question,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        cost_usd=cost_usd,
        status="pending",
    )

    async with AsyncSessionLocal() as db:
        db.add(trace)
        await db.commit()

    # enqueue eval job
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        redis = await create_pool(RedisSettings.from_dsn(os.environ.get("REDIS_URL", "redis://localhost:6379")))
        await redis.enqueue_job("run_eval", str(trace.id))
        await redis.close()
    except Exception:
        pass  # eval is best-effort; proxy must not fail


@router.post("/chat/completions")
async def proxy_chat(request: Request, background_tasks: BackgroundTasks) -> Response:
    if not OPENAI_API_KEY:
        raise HTTPException(status_code=503, detail="OPENAI_API_KEY not configured")

    body = await request.json()
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }

    start = time.perf_counter()
    async with httpx.AsyncClient(timeout=120.0) as client:
        upstream = await client.post(
            f"{UPSTREAM_BASE}/chat/completions",
            json=body,
            headers=headers,
        )
    latency_ms = (time.perf_counter() - start) * 1000

    if upstream.status_code != 200:
        return Response(
            content=upstream.content,
            status_code=upstream.status_code,
            media_type="application/json",
        )

    result = upstream.json()
    background_tasks.add_task(_persist_and_enqueue, body, result, latency_ms)

    return Response(content=upstream.content, media_type="application/json")
