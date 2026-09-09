# ERP Intelligence Dashboard — Backend

> AI-Powered Decision-Support System for an Internet Service Provider (ISP), built on top of an Enterprise Resource Planning (ERP) database.

[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![SQLModel](https://img.shields.io/badge/SQLModel-0.0.21+-blue.svg)](https://sqlmodel.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-16%20%2B%20pgvector-336791.svg?logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![LangGraph](https://img.shields.io/badge/AI-LangGraph%20%2B%20Gemini%20%2F%20OpenAI-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Tests](https://img.shields.io/badge/Tests-54%20Passed%20(100%25)-brightgreen.svg)]()
[![Types](https://img.shields.io/badge/Type%20Safety-Pyright%20Verified%20(0%20errors)-blueviolet.svg)]()

---

## 📌 Daftar Isi

1. [Gambaran Sistem](#-gambaran-sistem)
2. [Arsitektur Sistem & Data Layer](#-arsitektur-sistem--data-layer)
3. [Modul Domain Bisnis & Audit BI](#-modul-domain-bisnis--audit-bi)
4. [Sistem Autentikasi Dashboard](#-sistem-autentikasi-dashboard)
5. [Tech Stack](#-tech-stack)
6. [Struktur Direktori Proyek](#-struktur-direktori-proyek)
7. [Panduan Instalasi & Menjalankan](#-panduan-instalasi--menjalankan)
   - [A. Prasyarat](#a-prasyarat)
   - [B. Setup Lingkungan Lokal (Bare Metal / Virtualenv)](#b-setup-lingkungan-lokal-bare-metal--virtualenv)
   - [C. Menjalankan via Docker Compose](#c-menjalankan-via-docker-compose)
   - [D. Setup Mock ERP Database (Live Ingestion)](#d-setup-mock-erp-database-live-ingestion)
   - [E. Panduan Tunneling Ngrok](#e-panduan-tunneling-ngrok)
8. [Pengujian & Penjaminan Kualitas](#-pengujian--penjaminan-kualitas)
9. [Dokumentasi API & Integrasi Frontend](#-dokumentasi-api--integrasi-frontend)
10. [Status Proyek](#-status-proyek)

---

## 🚀 Gambaran Sistem

Backend **ERP Intelligence Dashboard** adalah platform analitik dan pendukung keputusan berbasis kecerdasan buatan (*AI decision-support system*) yang dirancang khusus untuk operasional penyedia layanan internet (ISP).

Sistem ini mengekstrak data operasional dari basis data ERP sumber (dikelola secara terpisah oleh tim Data Engineering), mentransformasikannya ke dalam **Feature Store** analitik PostgreSQL, melatih dan menjalankan model prediktif **Machine Learning (XGBoost)**, mengeksekusi agregasi SQL langsung berkinerja tinggi (**Direct SQL Datastore Analytics**), mengorkestrasikan **LangGraph AI Agents** dengan *Safe SQL Tools*, mensintesis rekomendasi naratif berbasis LLM (**Google Gemini / OpenAI / Rule-Based Fallback**), dan menghasilkan visualisasi grafik interaktif **Vega-Lite v5** serta tabel audit tabular yang disajikan melalui REST API **FastAPI**.

---

## 🏛 Arsitektur Sistem & Data Layer

Aliran data sistem terbagi ke dalam lima zona berurutan:

```mermaid
flowchart LR
    subgraph Z1["Zone 1: ERP Data Provisioning"]
        ERP[(External Source ERP)] -->|Batch Watermark Sync| EXT[Extractors & Transformers]
        EXT -->|Idempotent Upsert| FS[(Feature Store PostgreSQL)]
    end

    subgraph Z2["Zone 2: Predictive ML & Analytics Layer"]
        FS -->|Direct SQL Aggregations| DAS[Direct Analytics Service]
        FS -->|Feature Snapshots| ML[MLOps Training & Inference]
        ML -->|Predictions & Risk Tiers| PRED[(prediction_customer_churn)]
    end

    subgraph Z3["Zone 3: LangGraph Agentic Layer"]
        PRED & FS -->|Domain Queries| AGT[LangGraph Agents + SafeSQLTool]
    end

    subgraph Z4["Zone 4: Insight Generation"]
        DAS & AGT -->|Grounded Evidence| LLM[Compiler: LLM Synthesis + Vega-Lite Specs]
    end

    subgraph Z5["Zone 5: Presentation API"]
        LLM -->|DataEnvelope| API[FastAPI REST API /api/v1/...]
        API -->|JSON Contract| FE[Frontend Dashboard]
    end
```

1. **Zone 1: ERP Data Provisioning (Batch Extraction & Ingestion)**
   - Ekstraksi *watermark-based* dari ERP sumber (atau generator mock internal jika mode offline aktif).
   - Skema Staging (`stg_*`) $\to$ Dimensi/Fakta SCD Type 2 (`dim_*`, `fact_*`) $\to$ Agregasi analitik (`feature_*`).
   - Dilengkapi audit logger `etl_batch_log` dan validasi kualitas `data_quality_log`.
2. **Zone 2: Predictive Machine Learning & Direct SQL Analytics**
   - **Direct Datastore Analytics**: Agregasi SQL analitik berkecepatan tinggi langsung terhadap tabel Feature Store untuk metriks, tren grafik, dan tabel audit.
   - **MLOps Pipeline**: Pelatihan XGBoost Churn Classifier, penjelasan faktor risiko (*risk factor explainer*), dan *model registry*.
3. **Zone 3: LangGraph Agentic Layer (Autonomous Reasoning)**
   - Agen modular per domain bisnis yang dilengkapi `SafeSQLQueryTool` (validasi AST SQL read-only, pembatasan kuota baris, dan proteksi injeksi query).
4. **Zone 4: Insight Synthesis & Visualization Engine**
   - Mensintesis temuan analitik ke dalam narasi eksekutif berbahasa Indonesia dengan rekomendasi strategis menggunakan Google Gemini 2.5/1.5 Flash atau OpenAI.
   - Menyediakan mesin *fallback deterministik rule-based* otomatis jika API eksternal mengalami kendala jaringan atau tanpa kuota/kunci API.
   - Menghasilkan spesifikasi visualisasi grafik deklaratif berbasis **Vega-Lite v5**.
5. **Zone 5: Presentation API (Standardized JSON Envelope)**
   - Semua respons dibungkus dalam schema standar `DataEnvelope[T]` (`data`, `error`, `meta`).
   - Menyediakan ringkasan eksekutif (*Overview*), drill-down per modul dengan parameter `?table=`, dan data tabular lengkap untuk audit (*BI audit table*).

---

## 📊 Modul Domain Bisnis & Audit BI

Backend menyajikan wawasan analitik mendalam pada modul operasional utama:

| Domain | Endpoint API | Metrik Utama (KPIs) | Visualisasi Grafik (Vega-Lite v5) | Tabel Audit / Tindak Lanjut (`?table=...`) |
|---|---|---|---|---|
| **Overview** | `/api/v1/dashboard/overview` | Active Customers, MRR, Net Cashflow, Unpaid AR, Collection Rate, Health Score | • Revenue vs Payment<br>• Customer Growth<br>• Package Mix<br>• Domain Health | • `revenue_at_risk` *(default)*: Top pelanggan menunggak<br>• `data_quality`: Log anomali integritas data |
| **Commercial** | `/api/v1/insights/commercial` | Active Customers, Active Subscriptions, MRR, Unpaid Customers, Tenure (avg), Churn Proxy | • Customer Growth<br>• Package Mix & MRR<br>• Sebaran Kota<br>• AR Aging<br>• Instalasi/Bulan<br>• Billing Day<br>• Tenure Distribution | • `top_unpaid` *(default)*: Ranking tunggakan piutang<br>• `revenue_at_risk`: Pelanggan aktif + overdue<br>• `customers_without_sub`: Pelanggan tanpa langganan<br>• `top_revenue`: Pelanggan pembayaran tertinggi |
| **Finance** | `/api/v1/insights/finance` | Net Cashflow, Total Invoiced, Total Paid, Outstanding AR, Collection Rate, DSO, Tax Collected, Partial Payment Rate | • Invoice vs Payment Trend<br>• AR Aging Breakdown<br>• Payment Method Mix<br>• Overdue Amount Trend<br>• Tax Trend | • `overdue_invoices` *(default)*: Faktur lewat jatuh tempo<br>• `discrepancies`: Selisih rekonsiliasi pembayaran |
| **Procurement** | `/api/v1/insights/procurement` | Total Belanja PO, Rata-rata Lead Time, PO Pending | Tren Lead Time & Kinerja Vendor | Riwayat Purchase Order (`po_number`, vendor, status, lead days) |
| **Inventory** | `/api/v1/insights/inventory` | Nilai Total Stok, Barang Kritis, Rasio Turn Over | Proyeksi Depresiasi Stok Gudang | Status & Audit SKU Gudang (`sku`, item, stok aktual, level reorder) |
| **Asset** | `/api/v1/insights/asset` | Indeks Kesehatan Aset, Aset Butuh Servis, Nilai Buku | Distribusi Status & Kesehatan Aset | Inventaris Aset Operasional (`asset_id`, perangkat, lokasi, kondisi) |
| **Service** | `/api/v1/insights/service` | Kepatuhan SLA, Rata-rata MTTR, Tiket Gangguan Aktif | Kepatuhan SLA per Kategori Insiden | Audit Tiket Gangguan NOC (`ticket_id`, problem, MTTR, status SLA) |

---

## 🔐 Sistem Autentikasi Dashboard

Sistem autentikasi menggunakan model **Single-Tier Dashboard Login (Tanpa Sistem Role atau Otorisasi Berjenjang)**:
- Kredensial disimpan langsung di dalam tabel database Feature Store `feature_store.dim_user`.
- Password dienkripsi menggunakan pustaka native **bcrypt** (tahan terhadap Python 3.14/modern hashing).
- Sesi dikelola dengan access token berstandar **JWT Bearer**.
- **Auto-Provisioning**: Saat backend dijalankan pertama kali, tabel dibuat secara otomatis dan akun default disuntikkan (*seeded*).

### Kredensial Pengguna Default:
- **Username / Email**: `admin@isp.net`
- **Password**: `SecretPassword123!`
- **Endpoint Login**: `POST /api/v1/auth/login`
- **Endpoint Profil**: `GET /api/v1/auth/me`

---

## 💻 Tech Stack

- **Framework Web & API**: FastAPI (Python 3.11 - 3.14) & Uvicorn (ASGI)
- **ORM & Data Layer**: SQLModel + SQLAlchemy 2.0 (Asyncio) + asyncpg
- **Database Utama**: PostgreSQL 16 + pgvector (Feature Store)
- **Task Scheduling**: APScheduler (Background cron & interval jobs)
- **Machine Learning**: XGBoost, Scikit-Learn, Pandas, NumPy, Joblib
- **Agentic AI**: LangGraph, LangChain Core
- **LLM Integration**: Google Gemini API (v1beta), OpenAI API / Ollama / vLLM, Deterministic Rule Engine
- **Spesifikasi Visualisasi**: Pydantic v2 + Vega-Lite v5 JSON Spec
- **Type Checker**: Pyright (Zero errors / 100% type safety)
- **Testing**: Pytest, Pytest-Asyncio, HTTPX

---

## 📁 Struktur Direktori Proyek

```
project/                                  ← Root repositori
├── README.md                             # Dokumentasi komprehensif sistem backend
├── docker-compose.yml                    # Orkestrasi Docker untuk PostgreSQL & Backend API
├── docs/                                 # Dokumentasi living ground truth
│   ├── api_contract.md                   # Kontrak API frontend-backend (Ground Truth)
│   ├── openapi.json                      # Dump skema OpenAPI resmi (sinkron dengan codebase)
│   ├── design_arsitektur.md              # Diagram arsitektur Mermaid
│   ├── feature_store_schema_design.md    # DDL & desain skema Feature Store
│   └── task.md                           # Rincian tahapan pembangunan sistem
├── mock_erp_data_engineer/               # Lingkungan mandiri database Mock ERP eksternal
│   ├── docker-compose.yml                # Database Mock ERP (port 5433)
│   ├── sql/                              # DDL (21 tabel DBML) & Realistic Seeding
│   └── scripts/verify_erp_db.py          # Skrip verifikasi tabel ERP sumber
└── backend/                              # Seluruh aplikasi FastAPI backend
    ├── requirements.txt                  # Dependensi Python
    ├── Dockerfile                        # Konfigurasi container backend
    ├── pytest.ini                        # Konfigurasi pengujian pytest
    ├── .env.example                      # Template variabel lingkungan
    ├── app/
    │   ├── main.py                       # Inisialisasi FastAPI & lifespan startup
    │   ├── core/                         # Konfigurasi, database session, security, error handler
    │   ├── models/                       # Definisi tabel SQLModel (staging, dim, fact, feature, log, user)
    │   ├── schemas/                      # Pydantic schemas (auth, dashboard, ingestion, ml, common)
    │   ├── ingestion/                    # Engine ekstraksi data ERP, transformator & background jobs
    │   ├── ml/                           # Pipeline pelatihan ML, inference & customer risk explainer
    │   ├── agents/                       # Agen LangGraph & SafeSQLQueryTool
    │   ├── insights/                     # Compiler wawasan, Direct SQL Analytics & chart generator
    │   │   ├── analytics_service.py      # Kueri agregasi SQL langsung ke datastore
    │   │   ├── chart_generator.py        # Generator visualisasi Vega-Lite v5
    │   │   ├── compiler.py               # Orchestrator wawasan & perakit InsightPackage
    │   │   └── llm_client.py             # Klien sintesis LLM Gemini / OpenAI / Fallback
    │   └── api/v1/routes/                # Router endpoint API (/auth, /dashboard, /insights, /ingestion, /ml)
    ├── scripts/                          # Skrip otomasi (export_openapi, init_db, dll.)
    └── tests/
        ├── unit/                         # Unit tests (agent tools, insight engine, ml pipeline)
        └── integration/                  # Integration tests (auth DB, API contract, direct analytics, live BI)
```

---

## 🛠 Panduan Instalasi & Menjalankan

### A. Prasyarat
- **Python**: Versi 3.11 s/d 3.14
- **PostgreSQL**: Versi 16+ (Lokal atau via Docker)
- **Node.js**: (Opsional, jika ingin menjalankan type-check `pyright`)
- **Docker & Docker Compose**: (Disarankan untuk isolasi database)

---

### B. Setup Lingkungan Lokal (Bare Metal / Virtualenv)

#### 1. Masuk ke direktori backend dan buat virtual environment:
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
```

#### 2. Pasang seluruh dependensi Python:
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

#### 3. Salin dan sesuaikan variabel lingkungan:
```bash
cp .env.example .env
```
> **Catatan Konfigurasi:**
> - Pastikan `POSTGRES_USER`, `POSTGRES_PASSWORD`, dan `POSTGRES_DB` sesuai dengan server PostgreSQL lokal Anda (default port: `5434`).
> - Masukkan `GEMINI_API_KEY` jika ingin menggunakan model LLM Gemini langsung. Jika dibiarkan kosong, backend otomatis memakai mode *deterministic rule-based fallback* yang aman dan cepat.
> - Biarkan `ERP_MOCK_DATA=true` jika ingin menjalankan ingestion secara lokal tanpa database ERP eksternal.

#### 4. Inisialisasi Basis Data & Seed User Default:
Jalankan skrip inisialisasi untuk membuat semua schema (`stg_*`, `dim_*`, `fact_*`, `feature_*`, `etl_*`) dan mendaftarkan user default:
```bash
python scripts/init_db.py
```

#### 5. Jalankan Backend Server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Server akan aktif di:
- **API Base URL**: `http://localhost:8000`
- **Swagger UI Interactive**: `http://localhost:8000/docs`
- **ReDoc Documentation**: `http://localhost:8000/redoc`

---

### C. Menjalankan via Docker Compose

Jika ingin menjalankan PostgreSQL Feature Store dan Backend API sekaligus di dalam kontainer:

```bash
# Dari root project
docker compose up -d --build
```
- PostgreSQL Feature Store akan berjalan di port host **`5434`**.
- Backend API akan aktif di port host **`8000`**.

Untuk menghentikan kontainer:
```bash
docker compose down
```

---

### D. Setup Mock ERP Database (Live Ingestion)

Jika Anda ingin menguji integrasi pipeline ingestion langsung terhadap database operasional ERP sungguhan (dikelola oleh data engineer):

```bash
# Buka terminal baru dan masuk ke folder mock ERP
cd mock_erp_data_engineer
docker compose up -d

# Verifikasi ketersediaan 21 tabel dan data seed ERP
python scripts/verify_erp_db.py
```
Database sumber ERP akan aktif di port **`5433`** (`postgresql://erp_user:erp_secret_123@localhost:5433/isp_erp_db`). Pada file `backend/.env`, ubah:
```ini
ERP_MOCK_DATA=false
ERP_DB_PORT=5433
```

---

### E. Panduan Tunneling Ngrok

Untuk menghubungkan API lokal ke Frontend publik / remote:

```bash
ngrok http 8000 --host-header="localhost:8000"
```

> **Tips Pemanggilan Curl:**
> Tambahkan header `ngrok-skip-browser-warning: 69420` agar pengujian `curl` tidak terhalang halaman peringatan ngrok free-tier:
> ```bash
> curl -s "https://<ngrok-domain>/api/v1/dashboard/overview" -H "ngrok-skip-browser-warning: 69420"
> ```

---

## 🧪 Pengujian & Penjaminan Kualitas

Seluruh endpoint, logika ML, integrasi agen, analitik langsung datastore, dan autentikasi telah diuji secara menyeluruh.

### Menjalankan Seluruh Rangkaian Pengujian:
```bash
cd backend
pytest tests/ -v
```
*Hasil: **54 passed** (100% lolos tanpa kegagalan).*

### Menjalankan Pengujian Spesifik:
```bash
# 1. Tes Direct SQL Datastore Analytics (Phase 1)
pytest tests/integration/test_direct_analytics.py -v

# 2. Tes Integrasi Wawasan BI Dashboard & Modul Domain
pytest tests/integration/test_phase4_api.py -v

# 3. Tes Autentikasi Basis Data (Login & Profil Sesi)
pytest tests/integration/test_auth_db.py -v

# 4. Tes Kepatuhan Kontrak API (API Contract Conformance)
pytest tests/integration/test_api_contract.py -v

# 5. Tes Pipeline MLOps & Machine Learning
pytest tests/integration/test_mlops_pipeline_real.py -v
```

### Verifikasi Tipe Data Statis (Type Safety):
```bash
npx pyright backend/app
```
*Hasil: **0 errors, 0 warnings, 0 informations**.*

---

## 📖 Dokumentasi API & Integrasi Frontend

Untuk pengembang Frontend, dokumentasi dan kontrak API tersinkronisasi secara otomatis:

1. **API Contract Markdown (Living Ground Truth)**:
   - Terletak di [`docs/api_contract.md`](docs/api_contract.md).
   - Memuat struktur amplop JSON standar `DataEnvelope`, header request, format error, serta payload contoh untuk seluruh modul.
2. **OpenAPI Specification (JSON Dump)**:
   - Terletak di [`docs/openapi.json`](docs/openapi.json).
   - Dapat diimpor langsung ke Postman, Insomnia, atau digunakan dengan `openapi-typescript` / Swagger Codegen.
3. **Ekspor Ulang Skema OpenAPI**:
   Jika terdapat penambahan rute atau modifikasi skema, ekspor ulang dengan:
   ```bash
   python backend/scripts/export_openapi.py
   ```

---

## 📈 Status Proyek

| Fase Pengembangan | Status | Keterangan |
|---|---|---|
| **Fase 1: Infrastruktur & Database** | 🟢 Selesai | PostgreSQL Feature Store DDL, koneksi asyncpg, CORS, dan middleware error. |
| **Fase 2: Pipeline Ingestion** | 🟢 Selesai | Batch extraction jobs, transformasi Staging $\to$ Dim/Fact SCD-2, APScheduler. |
| **Fase 3: ML & LangGraph Integration** | 🟢 Selesai | XGBoost churn model, MLOps registry, agen LangGraph dengan SafeSQLTool, Insight Compiler. |
| **Phase 1: Direct Datastore Analytics** | 🟢 Selesai | Agregasi SQL langsung untuk Overview, Commercial, dan Finance dengan 10+ grafik Vega-Lite v5 dan filter `?table=`. |
| **Autentikasi Dashboard (Role-Free)** | 🟢 Selesai | Login basis data via `feature_store.dim_user`, enkripsi bcrypt, token JWT, auto-seed. |
| **Fase 5: Stabilisasi & Deployment** | 🟢 Siap | 54 tes integrasi & unit lolos (100%), type safety Pyright 100%, konfigurasi Docker Compose & Ngrok siap pakai. |

---

**Dikembangkan untuk Proyek Kerja Praktik (KP) — ISP Intelligence & Decision Support System.**
