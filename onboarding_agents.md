# Agent Onboarding — ERP Intelligence Dashboard Backend

This document captures everything a new agent needs to understand this project and work on it correctly. Read this before making any changes.

---

## 1. Project Purpose

This is the **backend** for an AI-powered ERP Intelligence Dashboard, built for an **ISP (Internet Service Provider)**. The ISP has an existing ERP system managing customers, subscriptions, billing, accounting, procurement, inventory, assets, and service operations.

This project does **not** touch the ERP system. Instead, it:
1. **Extracts** data from the ERP via scheduled batch queries (read-only access)
2. **Stores** it in a purpose-built **Feature Store** (PostgreSQL, owned by this project)
3. **Runs ML predictions** (churn, cash flow forecast, stockout risk, etc.)
4. **Orchestrates AI agents** (one LangGraph agent per business domain) to reason about the data
5. **Generates insights** (LLM narrative + chart specs) and validates them
6. **Exposes** insights via a FastAPI REST API for a separate frontend dashboard

The frontend is in a **separate repository** and is not part of this project's scope.

---

## 2. Architecture (5 Zones)

The system flows through five logical zones. Understanding this flow is critical:

### Zone 1: ERP Data Provisioning
- Source ERP database is **external and read-only**. Managed by a different team (data engineers).
- Data is pulled via **batch queries** using incremental extraction (`updated_at` / `created_at` watermarks).
- Extracted data lands in a **staging layer** (`staging.*` tables), then flows to dimension and fact tables.
- Six ERP domains are covered:
  - **Commercial/CRM**: Customer, Contract, Subscription, Billing
  - **Finance**: AR, AP, General Ledger, Cash Flow
  - **Procurement**: PR, PO, Vendor, Goods Receipt
  - **Inventory**: Stock, Warehouse, Material, Stock Movement
  - **Asset Management**: Network/Office Assets, Maintenance, Depreciation
  - **Service/Operations**: Service Order, Work Order, SLA, Tickets

### Zone 2: Predictive ML Layer
- Domain-specific models consume **ML-ready feature tables** (`feature_store.feature_*`).
- Planned models: Churn Prediction (XGBoost), Revenue Forecast (time series), Collection Risk, Cash Flow Forecast, Vendor Risk, Stockout Risk, Demand Forecast, Predictive Maintenance, SLA Breach Prediction, Work Order Delay.
- Labels are in **separate tables** (`label_*`) to prevent data leakage during training.

### Zone 3: LangGraph Agentic Layer
- One **LangGraph agent** per ERP domain (6 total).
- Agents share an **ERP Query Tool** for SQL-based data access.
- The **Service agent** has additional tools: Network Monitoring, Network Topology, and Qdrant (NOC ticket history via vector search — requires pgvector or Qdrant).

### Zone 4: Insight Generation Engine
- A **LangGraph State Compiler** aggregates outputs from all agents.
- **LLM API** (OpenAI/Gemini) synthesizes natural-language narratives.
- **Chart Spec Generator** produces Vega-Lite or Plotly JSON specs.
- A **Response Validator** ensures LLM output conforms to expected dashboard format before delivery.

### Zone 5: Presentation API
- FastAPI endpoints serve validated insight packages to the frontend.
- Main dashboard endpoint + per-module drill-down endpoints.
- Optional: manual refresh trigger and dynamic Q&A endpoint.

---

## 3. Feature Store Schema

The Feature Store is the **data backbone** of the project. Its schema is documented in detail in [`docs/feature_store_schema_design.md`](docs/feature_store_schema_design.md).

### Layer Structure
```
[ERP Source DB] --(batch query)--> [staging.*] --> [dim_* + fact_*] --> [feature_* (ML-ready)]
                                                                    --> [label_* (training targets)]
```

### Key Design Principles (do not violate these)
1. **Decoupled from source** — Feature Store never queries the ERP at runtime. All data is pre-extracted.
2. **Point-in-time correct** — Every row has an explicit `snapshot_date`. This prevents data leakage in ML training.
3. **Snapshot over realtime** — Periodic snapshot fact tables, not streaming/CDC.
4. **ML-ready + BI-ready** — Wide denormalized `feature_*` tables for ML, normalized `fact_*`/`dim_*` for BI queries.

### Table Naming Conventions
| Prefix | Layer | Purpose |
|---|---|---|
| `stg_` | Staging | 1:1 mirror of extracted source data |
| `dim_` | Dimension | SCD Type 2 slowly changing dimensions |
| `fact_` | Fact/Snapshot | Periodic snapshot facts (point-in-time) |
| `feature_` | ML-ready | Wide, denormalized feature tables |
| `label_` | Labels | Supervised learning targets (separate from features) |

### Mandatory Metadata Columns
- Every fact/feature table: `snapshot_date` (or period equivalent) + `batch_id`
- Surrogate keys: `*_key` suffix (e.g., `customer_key`)
- Natural keys from source: `*_id` suffix (e.g., `customer_id`)

### Schemas
- `staging` — Staging tables
- `feature_store` — Everything else (dimensions, facts, features, labels, metadata)

### Refresh Cadences
| Table | Frequency |
|---|---|
| `fact_subscription_snapshot` | Daily |
| `fact_billing_monthly` | Monthly (after billing cycle) |
| `fact_cashflow_monthly` | Monthly (after month close) |
| `fact_inventory_snapshot` | Weekly |
| `feature_customer_churn` | Weekly |
| `feature_cashflow_forecast` | Monthly |

### Idempotency
All jobs **must** use `INSERT ... ON CONFLICT ... DO UPDATE` to be safely re-runnable.

---

## 4. Tech Stack

| Component | Technology | Notes |
|---|---|---|
| API Framework | FastAPI (Python) | Async |
| ORM / DB Driver | SQLModel + asyncpg | PostgreSQL async driver |
| Database | PostgreSQL | Feature Store. pgvector extension for RAG/embeddings |
| Task Scheduler | APScheduler / Celery + Redis | Not finalized — either is acceptable for MVP |
| AI Agents | LangGraph + LangChain | One graph per domain |
| LLM API | OpenAI / Gemini | For narrative synthesis |
| Validation | Pydantic | Request/response schemas, LLM output validation |
| Charts | Vega-Lite (primary) / Plotly | JSON chart specs sent to frontend for rendering |
| Vector DB | Qdrant | NOC ticket history for the Service agent |
| ML | XGBoost, time-series libs | Not yet specified in detail |

---

## 5. Scope & Boundaries

### In scope (this project)
- Feature Store database (PostgreSQL) — schema, migrations, data models
- ETL/ingestion pipeline — extraction jobs, transformations, scheduling
- ML model integration — training pipelines, inference endpoints
- LangGraph agents — per-domain agent configuration and tools
- Insight generation — LLM synthesis, chart spec construction, validation
- FastAPI REST API — dashboard and module endpoints
- Auth middleware — JWT/OAuth
- API documentation — OpenAPI/Swagger

### Out of scope
- **Frontend/Dashboard UI** — Separate repository, separate team
- **ERP database** — Externally managed, read-only access only
- **Data engineering infrastructure** — Source DB is someone else's responsibility
- **Network monitoring systems** — External data source for Service agent

### MVP Focus (from `task.md`)
The MVP uses a **batch query approach** — no CDC, no streaming, no real-time. Insights are built from periodic snapshots. The recommended starting point is the **subscription + billing** domain (most directly useful for churn prediction).

---

## 6. Important Constraints & Caveats

### Database
- The Feature Store is a **separate database** from the ERP. Never assume a live connection to source at inference/dashboard time.
- `pgvector` extension is needed if vector search is used locally (for RAG). Alternatively, Qdrant handles this externally.
- Partitioning by `RANGE (snapshot_date)` is planned for large fact tables.

### Data Extraction
- Extraction uses **watermark-based incremental queries** (`updated_at` for mutable tables, `created_at` for append-only tables).
- Watermarks are tracked in `etl_batch_log`.
- `etl_batch_log` and `data_quality_log` should be implemented **first** — before any fact/feature tables are populated.

### ML / Labels
- Labels (`label_*` tables) are **intentionally separated** from features to prevent data leakage.
- Feature tables use `snapshot_date` for point-in-time correctness — features must only use data available **up to** that snapshot date.

### Known Gaps (from schema design doc, Section 7)
- **No support ticket/complaint table** exists in the source ERP schema. This is a strong churn signal and needs to be sourced separately (or confirmed with the data engineering team).
- **No explicit status change history** in the source ERP (no audit trail for customer status transitions). SCD Type 2 in the Feature Store will only capture changes **from the first extraction onward**, not historical changes before the system starts running.

### Frontend Integration
- The frontend expects: **narrative text** (from LLM) + **chart JSON specs** (Vega-Lite/Plotly) per module.
- API responses should follow a **consistent JSON structure** (standardized error handling).
- Swagger/OpenAPI documentation should be generated so the frontend team can mock and integrate independently.
- CORS must be configured since the frontend is in a separate repository/domain.

---

## 7. Development Sequence

Per `task.md`, work proceeds in this order:

1. **Phase 1: Infrastructure** — FastAPI project setup, env config, CORS, PostgreSQL connection + Feature Store DDL execution, auth middleware
2. **Phase 2: Ingestion Pipeline** — Extraction scripts (watermark-based), staging → dimension/fact upserts, scheduler setup, ETL logging
3. **Phase 3: ML & Agents** — ML model integration, LangGraph agent setup per module, insight engine (compiler + LLM + chart gen + validator)
4. **Phase 4: API Endpoints** — Main dashboard endpoint, per-module drill-down, optional manual trigger/Q&A, Swagger docs
5. **Phase 5: Stabilization** — Unit tests (extraction logic), integration tests (API response structure), CI/CD, staging deployment

**Recommended starting order within Phase 2**: Subscription + Billing domain first (highest value for churn prediction MVP), then expand to Accounting (cash flow) and Inventory.

---

## 8. Directory Map

Dokumentasi dan codebase dipisahkan secara eksplisit. Satu-satunya direktori kode adalah `backend/`.

```
project/                            ← root repo
├── README.md
├── onboarding_agents.md            ← dokumen ini
├── docs/                           ← source-of-truth dokumentasi
│   ├── task.md                     #   development phases & tech stack
│   ├── design_arsitektur.md        #   architecture diagram (Mermaid)
│   └── feature_store_schema_design.md  #   Feature Store DDL & schema
│
└── backend/                        ← seluruh codebase backend (Python)
    ├── .gitignore
    ├── app/                        ← FastAPI application package
    │   ├── api/v1/routes/          →  route handlers per modul (dashboard, commercial, finance, ...)
    │   ├── core/                   →  config, exceptions, logging, security (JWT/OAuth)
    │   ├── models/                 →  SQLModel table definitions (mirror Feature Store DDL)
    │   ├── schemas/                →  Pydantic request/response models
    │   ├── ingestion/
    │   │   ├── extractors/         →  watermark-based ERP query builders per domain
    │   │   ├── transformers/       →  staging → dim/fact → feature logic per domain
    │   │   └── jobs/               →  scheduled job definitions (scheduler entry point)
    │   ├── agents/
    │   │   └── tools/              →  shared agent tools (ERP SQL query tool, Qdrant, dll.)
    │   │   (+ file per domain: commercial, finance, procurement, inventory, asset, service)
    │   ├── ml/
    │   │   ├── models/             →  model class definitions
    │   │   ├── training/           →  training pipelines
    │   │   └── inference/          →  inference / prediction logic
    │   └── insights/               →  compiler, LLM narrative, chart spec generator, validator
    ├── alembic/versions/           ← migration files (Alembic)
    └── tests/
        ├── unit/                   →  unit tests (extraction logic, transformers, dll.)
        └── integration/            →  integration tests (API response structure, DB)
```

> **Status saat ini:** semua direktori berisi `.gitkeep` — belum ada kode. Implementasi dimulai pada Phase 1.

---

## 9. Conventions & Decisions

- **Language**: Python (all backend code)
- **Async**: Use async where possible (asyncpg, FastAPI async endpoints)
- **Database schema**: `staging` schema for staging tables, `feature_store` schema for everything else
- **API response format**: Consistent JSON structure with standardized error handling (not yet defined in detail)
- **Auth**: JWT or OAuth (exact implementation TBD)
- **Scheduler**: APScheduler or Celery — decision deferred to implementation phase
- **LLM provider**: OpenAI or Gemini — decision deferred, should be abstracted behind an interface

---

## 10. Open Questions

These are unresolved items identified from the documentation that may need decisions during implementation:

1. **ERP access mechanism** — Direct read-only DB connection vs. scheduled file exports (CSV/Parquet)?  Needs confirmation from data engineering team.
2. **Scheduler choice** — APScheduler (simpler, in-process) vs. Celery+Redis (distributed, more infrastructure)? Depends on deployment constraints.
3. **LLM provider** — OpenAI vs. Gemini? Should the integration be provider-agnostic from the start?
4. **Service domain data sources** — Support tickets, network monitoring, topology — where do these come from? No tables exist in the current ERP schema.
5. **Vector search** — pgvector (in PostgreSQL) vs. external Qdrant instance? Both are mentioned in docs.
6. **Auth specifics** — JWT vs. OAuth flow details, user management, role-based access?
7. **API response schema** — Exact structure of the validated insight package (narrative + charts + metadata)?
8. **ML model serving** — Internal functions vs. separate microservice? `task.md` mentions both possibilities.
