Tech Stack:
* **API & Web Framework: FastAPI (Python)**
* **Data ORM & Database Driver: SQLModel + asyncpg (PostgreSQL)**
* **Task Scheduler & Data Ingestion: APScheduler / Celery + Redis**
* **AI Agentic Framework: LangGraph (+ LangChain)**
* **Validation & Chart Spec Generator: Pydantic + Vega-Lite**



Berikut adalah urutan fase pekerjaan (tanpa estimasi waktu) untuk mengukur dan mengelola *scope* dari hulu ke hilir:

### Fase 1: Fondasi Infrastruktur & Database

Fase ini berfokus pada persiapan *environment* agar siap menampung data dan menerima *request*.

* **Inisiasi Repository & Framework:** Setup *project backend* (misalnya menggunakan FastAPI/Python atau Golang), konfigurasi *environment variables*, dan penanganan CORS agar *frontend* di repo terpisah bisa berkomunikasi.
* **Koneksi & Migrasi Database:** Setup koneksi ke PostgreSQL (termasuk ekstensi `pgvector` jika dipakai untuk NOC/RAG) dan mengeksekusi DDL skema *Feature Store* (Staging, Dimension, Fact, ML-Ready, dan Log).
* **Setup Middleware & Keamanan:** Pembuatan *middleware* untuk autentikasi (JWT/OAuth) dan *error handling* standar (struktur *response* JSON yang konsisten).

### Fase 2: Pembangunan Pipeline Ingestion (Tembak Query)

Karena Anda menggunakan pendekatan *batch query* untuk MVP, *backend* perlu memiliki mekanisme penjadwalan.

* **Pembuat Job Ekstraksi:** Menulis skrip untuk menembak DB ERP (dengan parameter *watermark* `updated_at`/`created_at`).
* **Transformasi ke Feature Store:** Logika *upsert* (INSERT ... ON CONFLICT) dari hasil ekstraksi ke layer Staging, lalu ke Dimension & Fact tables.
* **Setup Scheduler:** Mengintegrasikan *task scheduler* (seperti Celery Beat, APScheduler, atau Cron standar) untuk menjalankan job harian, mingguan, dan bulanan.
* **Sistem Logging:** Mengimplementasikan pencatatan ke `etl_batch_log` dan validasi dasar ke `data_quality_log` setiap kali *job* selesai.

### Fase 3: Integrasi Machine Learning & LangGraph (AI Layer)

Fase ini merealisasikan arsitektur agen dan prediksi data.

* **Integrasi Model Prediktif:** Membuat jembatan (bisa *internal function* atau memanggil *service* ML terpisah) untuk menghitung prediksi (*churn*, *cash flow*, *stockout*) dari tabel *ML-Ready*.
* **Setup LangGraph & Agent:** Mengonfigurasi agen untuk masing-masing modul (Commercial, Finance, Asset, dll.) beserta *tools*-nya (akses DB lewat *SQL Query Tool*, akses Qdrant untuk histori tiket).
* **Engine Sintesis & Visualisasi:** Membangun *Compiler* untuk merangkum state LangGraph, memanggil API LLM (OpenAI/Gemini) untuk membuat narasi *insight*, dan mengonstruksi spesifikasi *chart* (Vega-Lite/Plotly) dalam bentuk JSON.
* **Validator Response:** Logika untuk memastikan *output* LLM valid sesuai format *dashboard* sebelum dikirim ke *frontend*.

### Fase 4: Pengembangan API Endpoint (Frontend Integration)

Membuat pintu masuk bagi *frontend* untuk mengambil *insight* yang sudah diproses.

* **API Dashboard Utama:** Endpoint untuk mengambil ringkasan tingkat tinggi (metrik utama dari seluruh modul).
* **API per Modul (Drill-down):** Endpoint spesifik untuk halaman Commercial, Finance, Procurement, Inventory, Asset, dan Service (mengembalikan data narasi LLM dan JSON untuk grafik).
* **API Eksekusi/Trigger (Opsional untuk MVP):** Endpoint agar *user* bisa memicu *refresh* data atau bertanya (tanya-jawab dinamis) ke *agent* secara manual melalui UI.
* **Dokumentasi API:** Pembuatan Swagger/OpenAPI spec agar tim *frontend* bisa langsung melakukan *mocking* dan integrasi tanpa harus menunggu *backend* 100% selesai.

### Fase 5: Stabilisasi & Deployment

* **Testing:** Penulisan *unit test* untuk logika ekstraksi dan *integration test* untuk memastikan API mengembalikan struktur JSON yang tepat.
* **CI/CD Pipeline:** Setup otomatisasi *build* dan *testing* pada *repository*.
* **Deployment Staging:** Mengangkat *backend*, *database*, dan *scheduler* ke *environment staging* agar tim *frontend* bisa menguji secara *end-to-end*.