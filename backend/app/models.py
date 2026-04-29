from __future__ import annotations
import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Float, Integer, DateTime,
    ForeignKey, Text, JSON, Uuid
)
from sqlalchemy.orm import relationship, DeclarativeBase


class Base(DeclarativeBase):
    pass


class Trace(Base):
    __tablename__ = "traces"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    model = Column(String(120), nullable=False, index=True)
    prompt = Column(Text, nullable=False)
    response = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    question = Column(Text, nullable=True)
    latency_ms = Column(Float, nullable=False)
    prompt_tokens = Column(Integer, nullable=False, default=0)
    completion_tokens = Column(Integer, nullable=False, default=0)
    cost_usd = Column(Float, nullable=False, default=0.0)
    status = Column(String(20), default="pending", nullable=False, index=True)
    extra_metadata = Column(JSON, nullable=True)

    eval_run = relationship("EvalRun", back_populates="trace", uselist=False)


class EvalRun(Base):
    __tablename__ = "eval_runs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    trace_id = Column(Uuid, ForeignKey("traces.id"), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    faithfulness = Column(Float, nullable=True)
    answer_relevancy = Column(Float, nullable=True)
    context_recall = Column(Float, nullable=True)
    context_precision = Column(Float, nullable=True)
    error = Column(Text, nullable=True)

    trace = relationship("Trace", back_populates="eval_run")


class ModelConfig(Base):
    __tablename__ = "model_configs"

    model_name = Column(String(120), primary_key=True)
    cost_per_input_token = Column(Float, nullable=False, default=0.000001)
    cost_per_output_token = Column(Float, nullable=False, default=0.000002)
    display_name = Column(String(200), nullable=True)
