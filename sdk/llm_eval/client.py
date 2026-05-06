from __future__ import annotations
import os
import httpx
from .models import TracePayload, TraceResponse

DEFAULT_BASE_URL = os.environ.get("LLM_EVAL_URL", "http://localhost:8000")


class EvalClient:
    def __init__(self, base_url: str = DEFAULT_BASE_URL, timeout: float = 5.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def send_trace(self, payload: TracePayload) -> TraceResponse | None:
        try:
            with httpx.Client(timeout=self.timeout) as client:
                r = client.post(
                    f"{self.base_url}/api/v1/traces",
                    json=payload.model_dump(),
                )
                r.raise_for_status()
                return TraceResponse(**r.json())
        except Exception:
            return None

    async def send_trace_async(self, payload: TracePayload) -> TraceResponse | None:
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                r = await client.post(
                    f"{self.base_url}/api/v1/traces",
                    json=payload.model_dump(),
                )
                r.raise_for_status()
                return TraceResponse(**r.json())
        except Exception:
            return None


_default_client: EvalClient | None = None


def get_client() -> EvalClient:
    global _default_client
    if _default_client is None:
        _default_client = EvalClient()
    return _default_client


def configure(base_url: str, timeout: float = 5.0) -> None:
    global _default_client
    _default_client = EvalClient(base_url=base_url, timeout=timeout)
