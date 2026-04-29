from __future__ import annotations

import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Trace
from ..schemas import TraceIn, TraceOut, _PRICING

router = APIRouter(prefix="/traces", tags=["traces"])

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")


@router.post("", response_model=TraceOut, status_code=201)
async def create_trace(payload: TraceIn, db: AsyncSession = Depends(get_db)) -> Trace:
    rates = _PRICING.get(payload.model, (0.000001, 0.000002))
    cost_usd = rates[0] * payload.prompt_tokens + rates[1] * payload.completion_tokens

    trace = Trace(
        id=uuid.UUID(payload.id) if payload.id else uuid.uuid4(),
        model=payload.model,
        prompt=payload.prompt,
        response=payload.response,
        context=payload.context,
        question=payload.question or payload.prompt,
        latency_ms=payload.latency_ms,
        prompt_tokens=payload.prompt_tokens,
        completion_tokens=payload.completion_tokens,
        cost_usd=cost_usd,
        status="pending",
        extra_metadata=payload.metadata or {},
    )
    db.add(trace)
    await db.commit()

    # Re-fetch with relationship eagerly loaded (db.refresh doesn't load relations)
    q = select(Trace).options(selectinload(Trace.eval_run)).where(Trace.id == trace.id)
    result = await db.execute(q)
    trace = result.scalar_one()

    # fire-and-forget eval job
    try:
        from arq import create_pool
        from arq.connections import RedisSettings
        pool = await create_pool(RedisSettings.from_dsn(REDIS_URL))
        await pool.enqueue_job("run_eval", str(trace.id))
        await pool.close()
    except Exception:
        pass

    return trace


@router.get("", response_model=list[TraceOut])
async def list_traces(
    model: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[Trace]:
    q = select(Trace).options(selectinload(Trace.eval_run)).order_by(desc(Trace.created_at))
    if model:
        q = q.where(Trace.model == model)
    if status:
        q = q.where(Trace.status == status)
    q = q.limit(limit).offset(offset)
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/{trace_id}", response_model=TraceOut)
async def get_trace(trace_id: str, db: AsyncSession = Depends(get_db)) -> Trace:
    q = select(Trace).options(selectinload(Trace.eval_run)).where(Trace.id == uuid.UUID(trace_id))
    result = await db.execute(q)
    trace = result.scalar_one_or_none()
    if not trace:
        raise HTTPException(status_code=404, detail="Trace not found")
    return trace
