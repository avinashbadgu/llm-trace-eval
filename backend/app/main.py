from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import engine
from .models import Base
from .routers import evals, traces
from .proxy import router as proxy_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


app = FastAPI(
    title="LLM Eval API",
    version="0.1.0",
    description="Evaluation pipeline: captures LLM traces, runs RAGAS metrics, exposes results.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:5173").split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(traces.router, prefix="/api/v1")
app.include_router(evals.router, prefix="/api/v1")
app.include_router(proxy_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
