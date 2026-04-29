<div align="center">

# llm-trace-eval

**A production-grade LLM observability and evaluation pipeline.**

Sits between your app and any LLM. Logs every request, scores it with RAGAS (faithfulness · relevancy · context recall), and surfaces results in a live React dashboard — with zero latency impact on your application.

[![Python](https://img.shields.io/badge/Python-3.11%2B-blue?logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react&logoColor=black)](https://react.dev)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

</div>

---

## What problem does this solve?

When you ship an LLM feature, you have no automatic way to know if answers are faithful to your source documents, relevant to the question asked, or drifting in quality over time. Teams building RAG pipelines in production build internal tooling for exactly this — this is that tool, open-sourced.

---

## System Architecture

```
Your App ──HTTP──► FastAPI Proxy Middleware ──► OpenAI / Anthropic
(Web / API / Voice)      │                      (GPT-4 / Claude)
                         │  log event
                         ▼
               ┌─────────────────────┐
               │  Async Eval Worker  │
               │  (ARQ + Redis)      │
               └──────┬──────┬───────┘
                       │      │       │
              RAGAS metrics  Cost   Latency
              Faithfulness   tracker profiler
              Relevancy      $/token  p50/p95/p99
              Context recall
                       │      │       │
                       └──────┴───────┘
                               │
                         PostgreSQL
                  (traces · eval_runs · model_configs)
                               │
                            query
                               │
                     React Dashboard
                  /api/v1/evals — live metrics
```

**Key design principle:** eval runs in the background — the proxy responds to your app immediately, RAGAS scoring happens asynchronously. Zero latency added to your LLM calls.

---

## Features

| Feature | Detail |
|---|---|
| **Proxy middleware** | Drop-in OpenAI-compatible endpoint — change one URL in your app, get full observability |
| **RAGAS evaluation** | Faithfulness, answer relevancy, context recall — scored by an LLM judge in the background |
| **Cost tracker** | Token count × model price for every trace, stored and queryable |
| **Latency profiler** | p50 / p95 / p99 per model, plotted live on the dashboard |
| **Live dashboard** | KPI cards, trend charts, radial score gauges, model breakdown bar chart |
| **Model compare** | Radar chart + grouped bar chart — side-by-side quality comparison across models |
| **Trace inspector** | Full prompt / context / response + per-metric scores in a detail pane |
| **`@track` decorator** | Wraps any function — works with OpenAI, Anthropic, LangChain, custom calls |
| **SQLite local dev** | Zero-config local run without PostgreSQL or Redis |
| **Dockerised** | `docker compose up --build` boots all 5 services |

---

## Quick Start

### Option A — Docker (recommended for full pipeline)

```bash
git clone https://github.com/counsellorpro/llm-trace-eval.git
cd llm-trace-eval
cp .env.example .env          # add OPENAI_API_KEY
docker compose up --build
```

| Service | URL |
|---|---|
| Dashboard | http://localhost:5173 |
| API + Swagger docs | http://localhost:8000/docs |
| LLM Proxy | http://localhost:8000/proxy/chat/completions |

### Option B — Local (SQLite, no infrastructure needed)

```bash
git clone https://github.com/counsellorpro/llm-trace-eval.git
cd llm-trace-eval/backend

python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

pip install fastapi "uvicorn[standard]" "sqlalchemy[asyncio]" aiosqlite httpx pydantic numpy python-dotenv
uvicorn app.main:app --reload --port 8000
```

In a second terminal:

```bash
cd llm-trace-eval/frontend
npm install && npm run dev
```

Open http://localhost:5173 — dashboard loads immediately with SQLite as the backend, no Postgres or Redis required.

---

## Usage

### 1. Route requests through the proxy

Change one line in your OpenAI client — everything else stays identical:

```python
from openai import OpenAI

# Before: client = OpenAI(api_key="sk-...")
# After:
client = OpenAI(
    base_url="http://localhost:8000/proxy",
    api_key="your-openai-key",
)

resp = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "What is the capital of France?"}],
)
print(resp.choices[0].message.content)
# → Trace logged, cost calculated, RAGAS eval queued — zero latency added
```

### 2. Use the `@track` decorator

Wrap any function that calls an LLM:

```python
from llm_eval import track, configure
from openai import OpenAI

configure(base_url="http://localhost:8000")
openai_client = OpenAI()

@track(question_arg="question", context_arg="context")
def ask_rag(question: str, context: str) -> str:
    resp = openai_client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"Context:\n{context}"},
            {"role": "user",   "content": question},
        ],
    )
    return resp.choices[0].message.content

answer = ask_rag(
    question="What is the boiling point of water?",
    context="Water boils at 100°C (212°F) at standard atmospheric pressure.",
)
# → (question, context, answer) triple auto-captured and sent to eval pipeline
```

Works with async functions too — the decorator detects and wraps `async def` automatically.

### 3. Push traces directly via the API

```bash
curl -X POST http://localhost:8000/api/v1/traces \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-4o-mini",
    "prompt": "What is RAG?",
    "question": "What is RAG?",
    "response": "RAG combines retrieval with generation for grounded LLM answers.",
    "context": "Retrieval-Augmented Generation was introduced by Lewis et al. 2020.",
    "latency_ms": 412.5,
    "prompt_tokens": 20,
    "completion_tokens": 18
  }'
```

---

## API Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/api/v1/traces` | Ingest a trace (question / context / answer + metadata) |
| `GET` | `/api/v1/traces` | List traces — filter by `model`, `status`; paginate with `limit`, `offset` |
| `GET` | `/api/v1/traces/{id}` | Full trace detail including RAGAS scores |
| `GET` | `/api/v1/evals/stats` | Dashboard aggregates: avg scores, p50/p95/p99, cost, model breakdown |
| `GET` | `/api/v1/evals` | List all eval runs |
| `GET` | `/api/v1/evals/{id}` | Single eval run |
| `POST` | `/proxy/chat/completions` | OpenAI-compatible proxy — intercepts, logs, forwards |
| `GET` | `/health` | Health check |

Interactive docs available at http://localhost:8000/docs (Swagger UI).

---

## Running Tests

```bash
cd backend
pip install pytest pytest-asyncio httpx aiosqlite
pytest -v
```

25 tests covering:
- Trace CRUD, cost calculation, model filtering, pagination
- Eval listing, dashboard stats aggregation, model-level filtering
- SDK: `@track` sync/async, OpenAI object extraction, cost calculation

---

## Project Structure

```
llm-trace-eval/
├── sdk/                          # pip install llm-eval-sdk
│   ├── llm_eval/
│   │   ├── __init__.py           # @track decorator — auto-detects OpenAI/Anthropic/plain str
│   │   ├── client.py             # Non-blocking HTTP client (sync + async)
│   │   └── models.py             # Pydantic TracePayload
│   └── pyproject.toml
│
├── backend/
│   ├── app/
│   │   ├── main.py               # FastAPI app + lifespan (auto-creates DB tables)
│   │   ├── proxy.py              # /proxy/chat/completions — OpenAI-compatible intercept
│   │   ├── eval_worker.py        # ARQ background tasks + RAGAS 0.1/0.2 pipeline
│   │   ├── models.py             # SQLAlchemy ORM (Trace, EvalRun, ModelConfig)
│   │   ├── schemas.py            # Pydantic I/O schemas + model pricing table
│   │   ├── database.py           # Async engine — SQLite locally, PostgreSQL in prod
│   │   └── routers/
│   │       ├── traces.py         # GET/POST /api/v1/traces
│   │       └── evals.py          # GET /api/v1/evals + /stats
│   ├── alembic/                  # DB migrations (versioned)
│   │   └── versions/
│   │       └── 0001_initial_schema.py
│   ├── tests/
│   │   ├── conftest.py           # Shared fixtures (in-memory SQLite, ASGI test client)
│   │   ├── test_traces.py        # 10 trace endpoint tests
│   │   ├── test_evals.py         # 9 eval + stats tests
│   │   └── test_sdk.py           # 8 SDK unit tests
│   ├── requirements.txt
│   ├── Dockerfile
│   └── pytest.ini
│
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.jsx     # KPI cards, latency/cost trend, RAGAS gauges, model bar chart
│       │   ├── Traces.jsx        # Filterable table + slide-out detail pane
│       │   └── Compare.jsx       # Radar chart + grouped bar — model vs model
│       ├── components/
│       │   ├── ScoreGauge.jsx    # Radial bar gauge (green/yellow/red by score)
│       │   └── StatusBadge.jsx   # Coloured status pill
│       ├── hooks/
│       │   └── useApi.js         # TanStack Query hooks (auto-refresh every 30s)
│       ├── App.jsx               # Router + nav
│       └── index.css             # Tailwind base + component classes
│   ├── package.json
│   ├── vite.config.js            # Vite proxy → backend:8000
│   └── Dockerfile
│
├── docker-compose.yml            # postgres · redis · backend · worker · frontend
├── .env.example
└── README.md
```

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| API | FastAPI + Pydantic v2 + Uvicorn | Async-native, fastest Python web framework |
| Database | PostgreSQL 16 / SQLite (dev) + SQLAlchemy 2 async + Alembic | Full async ORM, portable between envs |
| Queue | ARQ (async Redis queue) | Pure-async, lightweight Celery alternative |
| Evaluation | RAGAS + OpenAI judge | Industry-standard RAG evaluation framework |
| Frontend | React 18 + Vite + Tailwind CSS + Recharts + TanStack Query | Fast dev, live data, no boilerplate |
| Infrastructure | Docker Compose | One command, reproducible |
| SDK | Pure Python + httpx + Pydantic v2 | Zero heavy dependencies |

---

## Roadmap

- [ ] Webhook alerts when faithfulness drops below threshold
- [ ] A/B experiment tracking (compare prompt versions, not just models)
- [ ] Export traces to CSV / Parquet for offline analysis
- [ ] LangChain / LlamaIndex callback integration
- [ ] Anthropic streaming proxy support
- [ ] Self-hosted RAGAS judge (no OpenAI key required)

---

## Contributing

PRs welcome. Please open an issue first for large changes.

```bash
# run tests before submitting
cd backend && pytest -v
```

---

## License

MIT — use it, fork it, ship it.

---

<div align="center">
Built with FastAPI · RAGAS · React · SQLAlchemy · ARQ
</div>
