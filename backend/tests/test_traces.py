"""Tests for /api/v1/traces endpoints."""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import AsyncClient

from tests.conftest import make_trace_payload

pytestmark = pytest.mark.asyncio


async def test_create_trace_returns_201(client: AsyncClient):
    resp = await client.post("/api/v1/traces", json=make_trace_payload())
    assert resp.status_code == 201
    data = resp.json()
    assert data["model"] == "gpt-4o-mini"
    assert data["status"] == "pending"
    assert "id" in data


async def test_create_trace_calculates_cost(client: AsyncClient):
    resp = await client.post(
        "/api/v1/traces",
        json=make_trace_payload(
            model="gpt-4o-mini",
            prompt_tokens=1000,
            completion_tokens=500,
        ),
    )
    assert resp.status_code == 201
    data = resp.json()
    # gpt-4o-mini: 0.00000015 * 1000 + 0.0000006 * 500 = 0.00015 + 0.0003 = 0.00045
    assert data["cost_usd"] == pytest.approx(0.00045, rel=1e-3)


async def test_create_trace_unknown_model_has_cost(client: AsyncClient):
    resp = await client.post("/api/v1/traces", json=make_trace_payload(model="some-new-model"))
    assert resp.status_code == 201
    assert resp.json()["cost_usd"] >= 0


async def test_list_traces_empty(client: AsyncClient):
    resp = await client.get("/api/v1/traces")
    assert resp.status_code == 200
    assert resp.json() == []


async def test_list_traces_returns_created(client: AsyncClient):
    await client.post("/api/v1/traces", json=make_trace_payload())
    await client.post("/api/v1/traces", json=make_trace_payload(model="gpt-4o"))

    resp = await client.get("/api/v1/traces")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


async def test_list_traces_filter_by_model(client: AsyncClient):
    await client.post("/api/v1/traces", json=make_trace_payload(model="gpt-4o-mini"))
    await client.post("/api/v1/traces", json=make_trace_payload(model="gpt-4o"))

    resp = await client.get("/api/v1/traces?model=gpt-4o")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["model"] == "gpt-4o"


async def test_get_trace_by_id(client: AsyncClient):
    created = (await client.post("/api/v1/traces", json=make_trace_payload())).json()
    trace_id = created["id"]

    resp = await client.get(f"/api/v1/traces/{trace_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == trace_id


async def test_get_trace_not_found(client: AsyncClient):
    import uuid
    resp = await client.get(f"/api/v1/traces/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_trace_without_context(client: AsyncClient):
    payload = make_trace_payload()
    del payload["context"]
    resp = await client.post("/api/v1/traces", json=payload)
    assert resp.status_code == 201
    assert resp.json()["context"] is None


async def test_list_traces_pagination(client: AsyncClient):
    for _ in range(5):
        await client.post("/api/v1/traces", json=make_trace_payload())

    resp = await client.get("/api/v1/traces?limit=2&offset=0")
    assert resp.status_code == 200
    assert len(resp.json()) == 2

    resp2 = await client.get("/api/v1/traces?limit=2&offset=2")
    assert resp2.status_code == 200
    assert len(resp2.json()) == 2
