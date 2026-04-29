"""Pydantic request/response schemas for the API layer."""
from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

# Token pricing: (input $/token, output $/token)
_PRICING: dict[str, tuple[float, float]] = {
    "gpt-4o": (0.000005, 0.000015),
    "gpt-4o-mini": (0.00000015, 0.0000006),
    "gpt-4-turbo": (0.00001, 0.00003),
    "gpt-4": (0.00003, 0.00006),
    "gpt-3.5-turbo": (0.0000005, 0.0000015),
    "claude-3-5-sonnet-20241022": (0.000003, 0.000015),
    "claude-3-5-haiku-20241022": (0.0000008, 0.000004),
    "claude-opus-4-7": (0.000015, 0.000075),
    "claude-sonnet-4-6": (0.000003, 0.000015),
}


class TraceIn(BaseModel):
    id: Optional[str] = None
    model: str
    prompt: str
    response: str
    context: Optional[str] = None
    question: Optional[str] = None
    latency_ms: float
    prompt_tokens: int = 0
    completion_tokens: int = 0
    metadata: dict = Field(default_factory=dict)


class EvalRunOut(BaseModel):
    id: UUID
    trace_id: UUID
    created_at: datetime
    faithfulness: Optional[float]
    answer_relevancy: Optional[float]
    context_recall: Optional[float]
    context_precision: Optional[float]
    error: Optional[str]

    model_config = {"from_attributes": True}


class TraceOut(BaseModel):
    id: UUID
    created_at: datetime
    model: str
    prompt: str
    response: str
    context: Optional[str]
    question: Optional[str]
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float
    status: str
    eval_run: Optional[EvalRunOut] = None

    model_config = {"from_attributes": True}


class LatencyPercentiles(BaseModel):
    p50: float
    p95: float
    p99: float


class DashboardStats(BaseModel):
    total_traces: int
    avg_faithfulness: Optional[float]
    avg_answer_relevancy: Optional[float]
    avg_context_recall: Optional[float]
    total_cost_usd: float
    latency: LatencyPercentiles
    traces_by_model: dict[str, int]
