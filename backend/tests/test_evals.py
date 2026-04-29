"""Tests for /api/v1/evals endpoints and stats."""
from __future__ import annotations

import uuid
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Trace, EvalRun
from tests.conftest import make_trace_payload

pytestmark = pytest.mark.asyncio


async def _seed_eval(db: AsyncSession, model: str = "gpt-4o-mini") -> tuple[Trace, EvalRun]:
    trace = Trace(
        model=model,
        prompt="test prompt",
        response="test response",
        question="test question",
        context="test context",
        latency_ms=200.0,
        prompt_tokens=10,
        completion_tokens=5,
        cost_usd=0.001,
        status="done",
    )
    db.add(trace)
    await db.flush()

    run = EvalRun(
        trace_id=trace.id,
        faithfulness=0.9,
        answer_relevancy=0.85,
        context_recall=0.8,
        context_precision=0.75,
    )
    db.add(run)
    await db.commit()
    return trace, run


async def test_list_evals_empty(client: AsyncClient):
    resp = await client.get("/api/v1/evals")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_evals_returns_run(client: AsyncClient, db_session: AsyncSession):
    _, run = await _seed_eval(db_session)
    resp = await client.get("/api/v1/evals")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["faithfulness"] == pytest.approx(0.9)
    assert data[0]["answer_relevancy"] == pytest.approx(0.85)


async def test_get_eval_by_id(client: AsyncClient, db_session: AsyncSession):
    _, run = await _seed_eval(db_session)
    resp = await client.get(f"/api/v1/evals/{run.id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == str(run.id)


async def test_get_eval_not_found(client: AsyncClient):
    resp = await client.get(f"/api/v1/evals/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_dashboard_stats_empty(client: AsyncClient):
    resp = await client.get("/api/v1/evals/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_traces"] == 0
    assert data["total_cost_usd"] == 0.0


async def test_dashboard_stats_with_data(client: AsyncClient, db_session: AsyncSession):
    await _seed_eval(db_session, model="gpt-4o-mini")
    await _seed_eval(db_session, model="gpt-4o")

    resp = await client.get("/api/v1/evals/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_traces"] == 2
    assert data["avg_faithfulness"] == pytest.approx(0.9)
    assert data["total_cost_usd"] == pytest.approx(0.002)
    assert "p50" in data["latency"]
    assert data["traces_by_model"]["gpt-4o-mini"] == 1
    assert data["traces_by_model"]["gpt-4o"] == 1


async def test_dashboard_stats_model_filter(client: AsyncClient, db_session: AsyncSession):
    await _seed_eval(db_session, model="gpt-4o-mini")
    await _seed_eval(db_session, model="gpt-4o")

    resp = await client.get("/api/v1/evals/stats?model=gpt-4o")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_traces"] == 1
    assert "gpt-4o" in data["traces_by_model"]


async def test_health_endpoint(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"
