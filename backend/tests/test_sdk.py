"""Tests for the llm-eval-sdk package."""
from __future__ import annotations

import sys
import os

# Make SDK importable from tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../sdk"))

import pytest
from unittest.mock import patch, MagicMock
from llm_eval.models import TracePayload
from llm_eval.client import EvalClient
from llm_eval import track, _calc_cost, _extract


def test_trace_payload_defaults():
    p = TracePayload(
        model="gpt-4o",
        prompt="Hello",
        response="Hi",
        latency_ms=100.0,
        prompt_tokens=5,
        completion_tokens=3,
    )
    assert p.model == "gpt-4o"
    assert p.context is None
    assert p.metadata == {}
    assert p.id is not None


def test_calc_cost_known_model():
    cost = _calc_cost("gpt-4o-mini", 1000, 500)
    assert cost == pytest.approx(1000 * 0.00000015 + 500 * 0.0000006)


def test_calc_cost_unknown_model():
    cost = _calc_cost("brand-new-model", 100, 50)
    assert cost > 0


def test_extract_string_result():
    response, model, pt, ct = _extract("hello world", None)
    assert response == "hello world"
    assert model == "unknown"


def test_extract_dict_result():
    d = {"response": "answer", "model": "gpt-4o", "prompt_tokens": 10, "completion_tokens": 5}
    response, model, pt, ct = _extract(d, None)
    assert response == "answer"
    assert model == "gpt-4o"
    assert pt == 10
    assert ct == 5


def test_extract_openai_object():
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = "the answer"
    mock.model = "gpt-4o"
    mock.usage.prompt_tokens = 20
    mock.usage.completion_tokens = 10
    response, model, pt, ct = _extract(mock, None)
    assert response == "the answer"
    assert model == "gpt-4o"
    assert pt == 20


def test_track_decorator_sync():
    with patch("llm_eval.client._default_client") as mock_client:
        mock_client.send_trace.return_value = None

        @track(question_arg="q")
        def ask(q: str) -> str:
            return "Paris"

        result = ask(q="Capital of France?")
        assert result == "Paris"


def test_track_decorator_preserves_return():
    with patch("llm_eval.get_client") as mock_get:
        mock_get.return_value = MagicMock(send_trace=lambda x: None)

        @track()
        def fn(question: str) -> str:
            return "42"

        assert fn(question="test") == "42"


@pytest.mark.asyncio
async def test_track_decorator_async():
    with patch("llm_eval.get_client") as mock_get:
        mock_get.return_value = MagicMock(send_trace=lambda x: None)

        @track()
        async def async_fn(question: str) -> str:
            return "async answer"

        result = await async_fn(question="test")
        assert result == "async answer"
