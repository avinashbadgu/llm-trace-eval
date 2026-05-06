"""llm-eval-sdk: Zero-latency LLM observability via the @track decorator."""
from __future__ import annotations

import time
import functools
import inspect
from typing import Callable, Any, Optional

from .client import EvalClient, get_client, configure
from .models import TracePayload, TraceResponse

__all__ = ["track", "configure", "EvalClient", "TracePayload"]

_MODEL_PRICING: dict[str, tuple[float, float]] = {
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


def _calc_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = _MODEL_PRICING.get(model, (0.000001, 0.000002))
    return rates[0] * prompt_tokens + rates[1] * completion_tokens


def track(
    *,
    question_arg: str = "question",
    context_arg: str = "context",
    model_override: Optional[str] = None,
) -> Callable:
    """
    Decorator that wraps any function calling an LLM, captures the
    (question, context, answer) triple and ships it to the eval backend.

    The decorated function must return either:
      - A string (the answer)
      - A dict with keys: response, model, prompt_tokens, completion_tokens
      - An OpenAI ChatCompletion object
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs) -> Any:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            all_args = bound.arguments

            question = all_args.get(question_arg) or ""
            context = all_args.get(context_arg)
            prompt = str(question)

            start = time.perf_counter()
            result = func(*args, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            _dispatch(result, prompt, question, context, latency_ms, model_override)
            return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs) -> Any:
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            all_args = bound.arguments

            question = all_args.get(question_arg) or ""
            context = all_args.get(context_arg)
            prompt = str(question)

            start = time.perf_counter()
            result = await func(*args, **kwargs)
            latency_ms = (time.perf_counter() - start) * 1000

            _dispatch(result, prompt, question, context, latency_ms, model_override)
            return result

        if inspect.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _dispatch(
    result: Any,
    prompt: str,
    question: str,
    context: Optional[str],
    latency_ms: float,
    model_override: Optional[str],
) -> None:
    response, model, prompt_tokens, completion_tokens = _extract(result, model_override)
    payload = TracePayload(
        model=model,
        prompt=prompt,
        response=response,
        context=context,
        question=question or prompt,
        latency_ms=latency_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    get_client().send_trace(payload)


def _extract(
    result: Any, model_override: Optional[str]
) -> tuple[str, str, int, int]:
    model = model_override or "unknown"
    prompt_tokens = 0
    completion_tokens = 0

    if isinstance(result, str):
        return result, model, prompt_tokens, completion_tokens

    if isinstance(result, dict):
        return (
            result.get("response", str(result)),
            result.get("model", model),
            result.get("prompt_tokens", 0),
            result.get("completion_tokens", 0),
        )

    # OpenAI ChatCompletion object
    if hasattr(result, "choices") and hasattr(result, "usage"):
        response = result.choices[0].message.content or ""
        model = getattr(result, "model", model)
        usage = result.usage
        prompt_tokens = getattr(usage, "prompt_tokens", 0)
        completion_tokens = getattr(usage, "completion_tokens", 0)
        return response, model, prompt_tokens, completion_tokens

    return str(result), model, prompt_tokens, completion_tokens
