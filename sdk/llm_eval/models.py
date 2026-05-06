from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
import uuid


class TracePayload(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    model: str
    prompt: str
    response: str
    context: Optional[str] = None
    question: Optional[str] = None
    latency_ms: float
    prompt_tokens: int
    completion_tokens: int
    metadata: dict = Field(default_factory=dict)


class TraceResponse(BaseModel):
    id: str
    status: str
