from __future__ import annotations

import uuid
from typing import Optional

import numpy as np
from fastapi import APIRouter, Depends, Query
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..database import get_db
from ..models import Trace, EvalRun
from ..schemas import EvalRunOut, DashboardStats, LatencyPercentiles

router = APIRouter(prefix="/evals", tags=["evals"])


@router.get("", response_model=list[EvalRunOut])
async def list_evals(
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> list[EvalRun]:
    q = (
        select(EvalRun)
        .options(selectinload(EvalRun.trace))
        .order_by(EvalRun.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(q)
    return result.scalars().all()


@router.get("/stats", response_model=DashboardStats)
async def dashboard_stats(
    model: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
) -> DashboardStats:
    trace_q = select(Trace)
    if model:
        trace_q = trace_q.where(Trace.model == model)
    trace_result = await db.execute(trace_q)
    traces = trace_result.scalars().all()

    total_traces = len(traces)
    total_cost = sum(t.cost_usd for t in traces)
    latencies = sorted(t.latency_ms for t in traces)

    def percentile(data: list[float], p: float) -> float:
        if not data:
            return 0.0
        return float(np.percentile(data, p))

    lat = LatencyPercentiles(
        p50=percentile(latencies, 50),
        p95=percentile(latencies, 95),
        p99=percentile(latencies, 99),
    )

    model_counts: dict[str, int] = {}
    for t in traces:
        model_counts[t.model] = model_counts.get(t.model, 0) + 1

    # Aggregate eval scores
    eval_q = select(EvalRun).join(Trace, EvalRun.trace_id == Trace.id)
    if model:
        eval_q = eval_q.where(Trace.model == model)
    eval_result = await db.execute(eval_q)
    evals = eval_result.scalars().all()

    def avg(vals: list[Optional[float]]) -> Optional[float]:
        filtered = [v for v in vals if v is not None]
        return sum(filtered) / len(filtered) if filtered else None

    return DashboardStats(
        total_traces=total_traces,
        avg_faithfulness=avg([e.faithfulness for e in evals]),
        avg_answer_relevancy=avg([e.answer_relevancy for e in evals]),
        avg_context_recall=avg([e.context_recall for e in evals]),
        total_cost_usd=total_cost,
        latency=lat,
        traces_by_model=model_counts,
    )


@router.get("/{eval_id}", response_model=EvalRunOut)
async def get_eval(eval_id: str, db: AsyncSession = Depends(get_db)) -> EvalRun:
    q = select(EvalRun).where(EvalRun.id == uuid.UUID(eval_id))
    result = await db.execute(q)
    run = result.scalar_one_or_none()
    if not run:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Eval run not found")
    return run
