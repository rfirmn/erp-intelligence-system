# ERP Intelligence Dashboard — Backend

> AI-powered decision-support system for an ISP, built on top of an existing ERP database.

## What This Project Does

This backend ingests data from an external ISP ERP system (managed by a separate data engineering team), transforms it into a purpose-built **Feature Store**, runs **predictive ML models** per business domain, orchestrates **LangGraph AI agents** to reason about predictions and data, and exposes the resulting insights through a **FastAPI** REST API consumed by a separate frontend dashboard.

The system covers **six ERP domains**: Commercial/CRM, Finance, Procurement, Inventory, Asset Management, and Service/Operations.

## Architecture Overview

The system flows through five zones:

```
1. ERP Data Provisioning    →  Batch extraction from source ERP DB into Feature Store
2. Predictive ML Layer      →  Domain-specific ML models (churn, cash flow, stockout, etc.)
3. LangGraph Agentic Layer  →  One agent per ERP domain with shared query tools
4. Insight Generation       →  LLM narrative synthesis + Vega-Lite chart spec generation
5. Presentation API         →  FastAPI endpoints serving validated insight packages
```

The source ERP database is **read-only and externally managed**. This project owns its own PostgreSQL Feature Store database (separate from the ERP). Data flows via scheduled batch jobs, not real-time connections.

See [`docs/design_arsitektur.md`](docs/design_arsitektur.md) for the full Mermaid architecture diagram.

## Tech Stack

| Layer | Technology |
|---|---|
| API & Web Framework | FastAPI (Python) |
| ORM & Database Driver | SQLModel + asyncpg |
| Database | PostgreSQL (+ pgvector for RAG/embeddings) |
| Task Scheduling | APScheduler / Celery + Redis |
| AI Agent Framework | LangGraph (+ LangChain) |
| Validation & Charts | Pydantic + Vega-Lite |
| ML (planned) | XGBoost, time-series models |
| External Context (Service domain) | Qdrant (NOC ticket history) |

## Directory Structure

```
project/                            ← root repo
├── README.md
├── onboarding_agents.md            # Panduan orientasi agent & arsitektur sistem
├── docs/                           # Dokumentasi & source of truth
│   ├── task.md                     # Development phases & tech stack
│   ├── design_arsitektur.md        # Architecture diagram (Mermaid)
│   ├── feature_store_schema_design.md  # Feature Store schema & DDL
│   ├── api_contract.md             # API Contract frontend-backend & envelope
│   └── openapi.json                # OpenAPI specification dump
└── backend/                        # Seluruh codebase backend (Python)
    ├── .gitignore
    ├── app/                        # FastAPI application package
    │   ├── api/v1/routes/          # Route handlers per modul (dashboard, commercial, ...)
    │   ├── core/                   # Config, security (JWT), logging, exceptions
    │   ├── models/                 # SQLModel table definitions (Feature Store DDL)
    │   ├── schemas/                # Pydantic request/response models
    │   ├── ingestion/
    │   │   ├── extractors/         # Watermark-based ERP query builders per domain
    │   │   ├── transformers/       # Staging → dim/fact → feature logic
    │   │   └── jobs/               # Scheduled job definitions
    │   ├── agents/
    │   │   └── tools/              # Shared agent tools (ERP SQL query, Qdrant, dll.)
    │   ├── ml/
    │   │   ├── models/             # Model class definitions
    │   │   ├── training/           # Training pipelines
    │   │   └── inference/          # Inference / prediction logic
    │   └── insights/               # Compiler, LLM narrative, chart generator, validator
    ├── alembic/versions/           # Database migrations (Alembic)
    ├── scripts/                    # Script pembantu (mis. export_openapi.py)
    └── tests/
        ├── unit/                   # Unit tests (extraction, transformation)
        └── integration/            # Integration tests (API contract, DB)
```

## Development Phases

The project follows five sequential phases (detailed in [`docs/task.md`](docs/task.md)):

1. **Infrastructure & Database** — Project setup, Feature Store DDL, auth middleware
2. **Ingestion Pipeline** — Batch extraction jobs, staging → feature transformations, scheduler
3. **ML & LangGraph Integration** — Predictive models, agent configuration, insight engine
4. **API Endpoints** — Dashboard API, per-module drill-down, optional Q&A trigger
5. **Stabilization & Deployment** — Testing, CI/CD, staging deployment

## Key Documentation

| Document | Purpose |
|---|---|
| [`onboarding_agents.md`](onboarding_agents.md) | Agent handoff document — architecture context, constraints, and caveats |
| [`docs/api_contract.md`](docs/api_contract.md) | Ground truth API contract between backend and frontend (envelope, mock endpoints, schemas) |
| [`docs/task.md`](docs/task.md) | Development phases, tech stack, scope |
| [`docs/design_arsitektur.md`](docs/design_arsitektur.md) | Full architecture diagram (Mermaid flowchart) |
| [`docs/feature_store_schema_design.md`](docs/feature_store_schema_design.md) | Feature Store schema design, DDL, extraction strategy, naming conventions |

## Status

🟡 **Early stage** — Project foundation and documentation. No application code implemented yet.
