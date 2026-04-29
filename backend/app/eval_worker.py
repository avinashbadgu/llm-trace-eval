"""
ARQ background worker.

Each trace that arrives triggers run_eval(), which:
  1. Pulls the Trace from Postgres.
  2. Builds a RAGAS EvaluationDataset (question / contexts / answer).
  3. Calls ragas.evaluate() — this itself calls an LLM judge (OpenAI by default).
  4. Persists the EvalRun scores.
  5. Sets Trace.status = "done" (or "error").

Run with:
    arq app.eval_worker.WorkerSettings
"""
from __future__ import annotations

import os
import uuid
import logging
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from .database import AsyncSessionLocal
from .models import Trace, EvalRun

log = logging.getLogger("eval_worker")

REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


async def run_eval(ctx: dict[str, Any], trace_id: str) -> dict[str, Any]:
    """Score a single trace with RAGAS metrics."""
    async with AsyncSessionLocal() as db:
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        q = select(Trace).where(Trace.id == uuid.UUID(trace_id))
        result = await db.execute(q)
        trace = result.scalar_one_or_none()

        if not trace:
            log.warning("Trace %s not found", trace_id)
            return {"error": "not_found"}

        # Mark as evaluating
        trace.status = "evaluating"
        await db.commit()

        scores: dict[str, float | None] = {
            "faithfulness": None,
            "answer_relevancy": None,
            "context_recall": None,
            "context_precision": None,
        }
        error_msg: str | None = None

        try:
            scores = await _run_ragas(trace)
        except Exception as exc:
            log.exception("RAGAS eval failed for trace %s: %s", trace_id, exc)
            error_msg = str(exc)

        eval_run = EvalRun(
            trace_id=trace.id,
            faithfulness=scores.get("faithfulness"),
            answer_relevancy=scores.get("answer_relevancy"),
            context_recall=scores.get("context_recall"),
            context_precision=scores.get("context_precision"),
            error=error_msg,
        )
        db.add(eval_run)
        trace.status = "error" if error_msg else "done"
        await db.commit()

    return {"trace_id": trace_id, "scores": scores, "error": error_msg}


async def _run_ragas(trace: Trace) -> dict[str, float | None]:
    """
    Attempt RAGAS 0.2+ API first, fall back gracefully.
    Returns a dict of metric_name -> score (0–1) or None.
    """
    if not trace.question and not trace.context:
        return {}

    question = trace.question or trace.prompt
    answer = trace.response
    context = trace.context or ""

    # Try RAGAS 0.2+ (ragas>=0.2)
    try:
        return await _ragas_v2(question, answer, context)
    except ImportError:
        pass

    # Fall back to RAGAS 0.1.x
    try:
        return await _ragas_v1(question, answer, context)
    except ImportError:
        log.warning("ragas not installed — returning empty scores")
        return {}


async def _ragas_v2(question: str, answer: str, context: str) -> dict[str, float | None]:
    from ragas import EvaluationDataset, SingleTurnSample, evaluate
    from ragas.metrics import Faithfulness, AnswerRelevancy

    metrics = [AnswerRelevancy()]
    if context.strip():
        metrics.append(Faithfulness())

    sample = SingleTurnSample(
        user_input=question,
        retrieved_contexts=[context] if context.strip() else [],
        response=answer,
    )
    dataset = EvaluationDataset(samples=[sample])

    # RAGAS uses LangChain LLMs under the hood; configure OpenAI key
    if OPENAI_API_KEY:
        import os as _os
        _os.environ.setdefault("OPENAI_API_KEY", OPENAI_API_KEY)

    result = evaluate(dataset, metrics=metrics)
    scores = result.to_pandas().to_dict(orient="records")[0]

    return {
        "faithfulness": _safe_float(scores.get("faithfulness")),
        "answer_relevancy": _safe_float(scores.get("answer_relevancy")),
        "context_recall": None,
        "context_precision": None,
    }


async def _ragas_v1(question: str, answer: str, context: str) -> dict[str, float | None]:
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import faithfulness, answer_relevancy

    data: dict[str, list] = {
        "question": [question],
        "answer": [answer],
        "contexts": [[context]] if context.strip() else [[""]],
    }
    dataset = Dataset.from_dict(data)

    metrics = [answer_relevancy]
    if context.strip():
        metrics.append(faithfulness)

    if OPENAI_API_KEY:
        import os as _os
        _os.environ.setdefault("OPENAI_API_KEY", OPENAI_API_KEY)

    result = evaluate(dataset, metrics=metrics)
    scores = result.to_pandas().to_dict(orient="records")[0]

    return {
        "faithfulness": _safe_float(scores.get("faithfulness")),
        "answer_relevancy": _safe_float(scores.get("answer_relevancy")),
        "context_recall": _safe_float(scores.get("context_recall")),
        "context_precision": _safe_float(scores.get("context_precision")),
    }


def _safe_float(v: Any) -> float | None:
    try:
        f = float(v)
        return None if f != f else f  # NaN check
    except (TypeError, ValueError):
        return None


class WorkerSettings:
    """ARQ worker configuration."""
    functions = [run_eval]
    redis_settings = RedisSettings.from_dsn(REDIS_URL)
    max_jobs = int(os.environ.get("ARQ_MAX_JOBS", "4"))
    job_timeout = int(os.environ.get("ARQ_JOB_TIMEOUT", "120"))
    keep_result = 3600  # keep job results for 1 hour
