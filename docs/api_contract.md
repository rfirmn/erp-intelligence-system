# API Contract — ERP Intelligence Dashboard

Dokumen ini adalah **Ground Truth** spesifikasi antarmuka komunikasi antara Backend (FastAPI) dan Frontend (Dashboard UI). Dokumen ini bersifat *living document* yang terus disinkronkan dengan schema backend (FastAPI / Pydantic).

---

## 1. Konvensi Dasar & Protokol

- **Base URL (Local)**: `http://localhost:8000/api/v1`
- **Format Pertukaran Data**: `application/json; charset=utf-8`
- **Zona Waktu & Tanggal**: ISO-8601 (`YYYY-MM-DDTHH:mm:ssZ` untuk timestamp, `YYYY-MM-DD` untuk tanggal snapshot/faktur).
- **Format Angka & Mata Uang**:
  - Kolom nilai kalkulasi / kuantitatif berupa tipe data `number` (float atau integer).
  - Kolom `formatted_value` (string) disediakan untuk kenyamanan rendering di UI (contoh: `"Rp 1.450.000.000"` atau `"98.4%"`).
- **CORS Support**: Diaktifkan untuk domain frontend (mis. `http://localhost:3000`, `http://localhost:5173`). Header yang didukung: `Authorization`, `Content-Type`, `X-Request-ID`.

---

## 2. Universal Response Envelope

Seluruh respons dari API (baik response sukses kode `2xx`, client error `4xx`, maupun server error `5xx`) **wajib** dibungkus menggunakan amplop seragam (*standardized envelope*).

### 2.1 Format Sukses (`HTTP 200 / 201`)
```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "c6a1b2c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "timestamp": "2026-09-04T22:45:00Z",
    "version": "v1"
  },
  "error": null
}
```

### 2.2 Format Gagal (`HTTP 4xx / 5xx`)
```json
{
  "success": false,
  "data": null,
  "meta": {
    "request_id": "c6a1b2c3-4d5e-6f7a-8b9c-0d1e2f3a4b5c",
    "timestamp": "2026-09-04T22:45:00Z",
    "version": "v1"
  },
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Payload request tidak memenuhi kriteria validasi.",
    "details": [
      {
        "field": "username",
        "issue": "Field wajib diisi dan minimal 3 karakter."
      }
    ]
  }
}
```

### 2.3 Katalog Standar Error Code
| Kode Status | Error Code | Keterangan |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Format body JSON tidak sesuai, tipe data salah, atau melanggar schema. |
| 400 | `BAD_REQUEST` | Operasi tidak dapat diproses karena logika bisnis tidak valid. |
| 401 | `UNAUTHORIZED` | Token autentikasi tidak disertakan, kedaluwarsa, atau tanda tangan tidak valid. |
| 403 | `FORBIDDEN` | Akun pengguna tidak memiliki hak akses pada resource yang diminta. |
| 404 | `NOT_FOUND` | Data atau rute endpoint tidak ditemukan. |
| 409 | `CONFLICT` | Terjadi konflik state (mis. ID batch yang sudah dieksekusi). |
| 422 | `UNPROCESSABLE_ENTITY` | Semantic validation error dari Pydantic parser. |
| 500 | `INTERNAL_SERVER_ERROR` | Kesalahan internal server yang tidak tertangani. |
| 503 | `DATABASE_UNAVAILABLE` | Koneksi database PostgreSQL Feature Store terputus atau timeout. |

---

## 3. Autentikasi & Otorisasi

Menggunakan mekanisme **OAuth2 Bearer Token (JWT)**.

Header yang wajib dikirim pada endpoint terlindungi:
```http
Authorization: Bearer <access_token>
```

> **Catatan Mode Development**: Jika flag `SECURITY_ENABLED=false` disetel di backend environment, middleware keamanan akan melewatkan autentikasi dan menganggap request berasal dari default development user (`admin@isp-intelligence.local`).

### 3.1 Login (Dapatkan Token)
- **Endpoint**: `POST /api/v1/auth/login`
- **Request Headers**: `Content-Type: application/json`
- **Request Body**:
  ```json
  {
    "username": "admin@isp.net",
    "password": "SecretPassword123!"
  }
  ```
- **Response Success (`200 OK`)**:
  ```json
  {
    "success": true,
    "data": {
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer",
      "expires_in": 86400,
      "user": {
        "id": "usr-001",
        "username": "admin@isp.net",
        "full_name": "System Administrator",
        "role": "admin"
      }
    },
    "meta": {
      "request_id": "8c454e99-873b-486a-8b89-13e2bb97f744",
      "timestamp": "2026-09-04T22:45:00Z",
      "version": "v1"
    },
    "error": null
  }
  ```

### 3.2 Profil Pengguna Saat Ini
- **Endpoint**: `GET /api/v1/auth/me`
- **Request Headers**: `Authorization: Bearer <access_token>`
- **Response Success (`200 OK`)**:
  ```json
  {
    "success": true,
    "data": {
      "id": "usr-001",
      "username": "admin@isp.net",
      "full_name": "System Administrator",
      "role": "admin",
      "permissions": ["dashboard:read", "commercial:read", "finance:read", "procurement:read", "inventory:read", "asset:read", "service:read"]
    },
    "meta": {
      "request_id": "8c454e99-873b-486a-8b89-13e2bb97f744",
      "timestamp": "2026-09-04T22:45:00Z",
      "version": "v1"
    },
    "error": null
  }
  ```

---

## 4. Health & System Readiness

- **Endpoint**: `GET /api/v1/health`
- **Keterangan**: Endpoint publik untuk monitoring liveness dan readiness backend serta koneksi database Feature Store.
- **Response Success (`200 OK`)**:
  ```json
  {
    "success": true,
    "data": {
      "status": "healthy",
      "timestamp": "2026-09-04T22:45:00Z",
      "version": "0.1.0",
      "environment": "development",
      "components": {
        "database": {
          "status": "connected",
          "latency_ms": 1.82,
          "pool_size": 5,
          "active_connections": 1
        },
        "feature_store": {
          "status": "ready",
          "schemas": ["staging", "feature_store"]
        }
      }
    },
    "meta": {
      "request_id": "7b0b2e8a-86c2-4806-bbfb-ff3487c69ec7",
      "timestamp": "2026-09-04T22:45:00Z",
      "version": "v1"
    },
    "error": null
  }
  ```

---

## 5. The Insight Package Contract (Frontend Integration Target)

Insight package adalah kontrak inti yang digunakan oleh frontend dashboard untuk menampilkan ringkasan eksekutif, metrik kartu (KPI), narasi penalaran LLM dari domain agent, dan visualisasi interaktif Vega-Lite.

### 5.1 Definisi Schema Objek
- **`module`**: `string` — Nama modul bisnis:
  - `"overview"`: Ringkasan lintas modul untuk Dashboard Utama.
  - `"commercial"`: Analisis churn pelanggan, retensi, dan pertumbuhan langganan.
  - `"finance"`: Analisis cash flow, piutang (AR Aging), dan penagihan.
  - `"procurement"`: Analisis lead time vendor, evaluasi risiko supplier, dan performa PO.
  - `"inventory"`: Analisis risiko kehabisan stok (stockout) dan tren pemakaian material.
  - `"asset"`: Analisis depresiasi perangkat, status pemeliharaan, dan prediksi kegagalan perangkat jaringan.
  - `"service"`: Analisis SLA breach, durasi tiket NOC, dan keterlambatan Work Order.
- **`as_of_date`**: `string (date)` — Tanggal data snapshot dasar (`YYYY-MM-DD`).
- **`executive_summary`**: `string` — Narasi tingkat tinggi 2-3 kalimat untuk pimpinan eksekutif.
- **`key_metrics`**: `Array<KeyMetric>` — Kartu-kartu KPI yang ditampilkan di grid atas dashboard:
  - `key`: Identifier unik metrik (e.g. `"mrr"`, `"churn_risk_count"`).
  - `label`: Label yang ditampilkan (e.g. `"Monthly Recurring Revenue"`).
  - `value`: Nilai numerik mentah (`1450000000`).
  - `formatted_value`: String ramah tampilan (`"Rp 1,45 M"`).
  - `unit`: Satuan (`"IDR"`, `"customers"`, `"%"`).
  - `change_percentage`: Persentase perubahan dibanding periode sebelumnya (`3.2`).
  - `trend`: `"up" | "down" | "neutral"`.
  - `status`: Indikator warna status (`"good" | "warning" | "critical"`).
- **`narrative_insights`**: `Array<NarrativeInsight>` — Wawasan mendalam berbasis alasan agen:
  - `id`: Identifier wawasan (e.g. `"ins-comm-001"`).
  - `domain`: Domain bisnis asal wawasan.
  - `severity`: `"info" | "warning" | "critical"`.
  - `title`: Judul temuan wawasan.
  - `narrative`: Teks penjelasan latar belakang dan penyebab berdasarkan inferensi agen.
  - `suggested_actions`: Array string berisi rekomendasi tindakan konkret yang disarankan.
- **`visualizations`**: `Array<Visualization>` — Grafik yang langsung dapat dirender oleh frontend:
  - `chart_id`: Identifier grafik (e.g. `"chart-churn-distribution"`).
  - `title`: Judul grafik.
  - `description`: Subjudul atau deskripsi data grafik.
  - `chart_library`: `"vega-lite" | "plotly"`.
  - `spec`: Objek JSON spesifikasi Vega-Lite v5 (berisi `$schema`, `mark`, `encoding`, `scale`, dll.).
  - `data`: Array objek data JSON yang di-binding langsung ke dalam spec Vega-Lite.
- **`audit_table`**: `AuditTable (opsional)` — Dataset tabular terstruktur untuk audit transparansi data mentah dan verifikasi total (BI Grid):
  - `title`: Judul tabel audit (e.g. `"Audit Portofolio Risiko Pelanggan (XGBoost Churn Profiling)"`).
  - `description`: Keterangan cakupan data audit transaksi / entitas.
  - `columns`: Array objek definisi kolom (`key`, `label`, `type`: `"text" | "number" | "currency" | "percentage" | "badge" | "date"`).
  - `rows`: Array objek record data baris untuk verifikasi angka total.
  - `total_records`: Total baris data yang diaudit.
- **`model_metadata`**: `Array<ModelMetadata>` — Metadata model machine learning penunjang:
  - `model_name`: Nama model (e.g. `"xgboost_churn_v1"`).
  - `version`: Versi model (e.g. `"1.0.0"`).
  - `prediction_window`: Jendela prediksi (e.g. `"30_days"`).
  - `confidence_score`: Nilai keyakinan / ROC-AUC / F1-score (`0.892`).
  - `last_trained_at`: Waktu pelatihan terakhir model.
- **`generated_at`**: `string (datetime)` — Waktu kompilasi paket wawasan.

---

## 6. Endpoints Wawasan (Production & Living Prototype)

### 6.1 Dashboard Utama Ringkasan Eksekutif (Production)
- **Endpoint**: `GET /api/v1/dashboard/overview`
- **Query Parameter**: `as_of_date` (opsional, format `YYYY-MM-DD`, default: tanggal snapshot terbaru).
- **Keterangan**: Mengambil wawasan ringkasan eksekutif makro lintas modul bisnis ISP yang dikompilasi oleh LangGraph Domain Agents dan LLM Synthesis Engine dengan visualisasi Vega-Lite v5.
- **Response Success (`200 OK`)**: Mengembalikan amplop standar dengan `data` bertipe [`InsightPackage`](#51-definisi-schema-objek).

### 6.2 Wawasan per Modul Bisnis (Production)
- **Endpoint**: `GET /api/v1/insights/{module}`
- **Path Parameter**: `module` (`overview`, `commercial`, `finance`, `procurement`, `inventory`, `asset`, `service`).
- **Query Parameter**: `as_of_date` (opsional, format `YYYY-MM-DD`).
- **Keterangan**: Mengambil paket wawasan terstruktur untuk modul bisnis terkait. Menggabungkan kartu KPI aktual, wawasan narasi berbasis bukti matematis model ML (TreeSHAP drivers), dan grafik interaktif Vega-Lite v5.
- **Response Success (`200 OK`)**: Mengembalikan amplop standar dengan `data` bertipe [`InsightPackage`](#51-definisi-schema-objek).

### 6.3 Ambil Wawasan Mock (Living Prototype / Offline Testing)
- **Endpoint**: `GET /api/v1/insights/mock/{module}`
- **Path Parameter**: `module` (salah satu dari: `overview`, `commercial`, `finance`, `procurement`, `inventory`, `asset`, `service`).
- **Keterangan**: Endpoint cepat untuk tim frontend melakukan pengujian layout tanpa perlu mengeksekusi pipeline LLM atau database.
- **Response Success (`200 OK`)**:
  ```json
  {
    "success": true,
    "data": {
      "module": "commercial",
      "as_of_date": "2026-09-01",
      "executive_summary": "Tingkat churn pelanggan segmen ritel diproyeksikan meningkat 2.4% pada kuartal mendatang.",
      "key_metrics": [
        {
          "key": "mrr",
          "label": "Monthly Recurring Revenue",
          "value": 1450000000.0,
          "formatted_value": "Rp 1,45 M",
          "unit": "IDR",
          "change_percentage": 3.2,
          "trend": "up",
          "status": "good"
        },
        {
          "key": "high_churn_risk",
          "label": "Pelanggan Risiko Tinggi",
          "value": 142,
          "formatted_value": "142 Pelanggan",
          "unit": "customers",
          "change_percentage": 12.5,
          "trend": "up",
          "status": "critical"
        }
      ],
      "narrative_insights": [
        {
          "id": "ins-comm-001",
          "domain": "commercial",
          "severity": "critical",
          "title": "Konsentrasi Risiko Churn pada Paket 50 Mbps",
          "narrative": "Model XGBoost mendeteksi 68 pelanggan paket 50 Mbps mengalami keterlambatan pembayaran >15 hari selama 2 bulan berturut-turut setelah penyesuaian tarif.",
          "suggested_actions": [
            "Kirimkan notifikasi penawaran diskon perpanjangan kontrak otomatis.",
            "Prioritaskan tim customer retention untuk menghubungi 20 akun teratas berdasarkan nilai tagihan."
          ]
        }
      ],
      "visualizations": [
        {
          "chart_id": "chart-churn-distribution",
          "title": "Distribusi Probabilitas Churn Pelanggan",
          "description": "Histogram probabilitas churn hasil prediksi model XGBoost",
          "chart_library": "vega-lite",
          "spec": {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "mark": "bar",
            "encoding": {
              "x": { "field": "risk_tier", "type": "nominal", "axis": { "title": "Tingkat Risiko" } },
              "y": { "field": "count", "type": "quantitative", "axis": { "title": "Jumlah Pelanggan" } },
              "color": {
                "field": "risk_tier",
                "type": "nominal",
                "scale": {
                  "domain": ["Rendah", "Sedang", "Tinggi"],
                  "range": ["#22c55e", "#eab308", "#ef4444"]
                }
              }
            }
          },
          "data": [
            { "risk_tier": "Rendah", "count": 1250 },
            { "risk_tier": "Sedang", "count": 340 },
            { "risk_tier": "Tinggi", "count": 142 }
          ]
        }
      ],
      "audit_table": {
        "title": "Audit Portofolio Risiko Pelanggan (XGBoost Churn Profiling)",
        "description": "Daftar akun pelanggan, estimasi probabilitas churn, dan pendorong risiko utama",
        "columns": [
          { "key": "customer_id", "label": "ID Akun", "type": "text" },
          { "key": "customer_name", "label": "Nama Pelanggan", "type": "text" },
          { "key": "city", "label": "Kota", "type": "text" },
          { "key": "churn_probability", "label": "Probabilitas Churn", "type": "percentage" },
          { "key": "risk_level", "label": "Tingkat Risiko", "type": "badge" },
          { "key": "primary_risk_driver", "label": "Faktor Pendorong Risiko", "type": "text" }
        ],
        "rows": [
          { "customer_id": "CUST-1013", "customer_name": "Customer #1013", "city": "Surabaya", "churn_probability": "84.2%", "risk_level": "HIGH", "primary_risk_driver": "Keterlambatan bayar >=2x (3 bln)" },
          { "customer_id": "CUST-1045", "customer_name": "Customer #1045", "city": "Bandung", "churn_probability": "76.5%", "risk_level": "HIGH", "primary_risk_driver": "Status pembayaran WORSENING" },
          { "customer_id": "CUST-1088", "customer_name": "Customer #1088", "city": "Jakarta", "churn_probability": "71.0%", "risk_level": "HIGH", "primary_risk_driver": "Downgrade paket 6 bulan terakhir" }
        ],
        "total_records": 3
      },
      "model_metadata": [
        {
          "model_name": "xgboost_churn_v1",
          "version": "1.0.0",
          "prediction_window": "30_days",
          "confidence_score": 0.892,
          "last_trained_at": "2026-08-28T03:00:00Z"
        }
      ],
      "generated_at": "2026-09-04T22:45:00Z"
    },
    "meta": {
      "request_id": "d1e2f3a4-b5c6-7d8e-9f0a-1b2c3d4e5f6a",
      "timestamp": "2026-09-04T22:45:00Z",
      "version": "v1"
    },
    "error": null
  }
  ```

---

## 7. Machine Learning & Predictive Intelligence Endpoints (Zone 2)

Endpoint ini melayani siklus pelatihan model machine learning dan inferensi prediksi risiko pelanggan (Customer Churn berbasis XGBoost).

### 7.1 Latih / Retrain Model Churn: `POST /api/v1/ml/models/churn/train`
- **Request Body**:
  ```json
  {
    "model_version": "1.0.0",
    "test_size_ratio": 0.2,
    "hyperparameters": {
      "max_depth": 4,
      "learning_rate": 0.05,
      "n_estimators": 100
    },
    "set_as_active": true
  }
  ```
- **Response Body (`data`)**:
  ```json
  {
    "model_name": "churn_xgboost",
    "model_version": "1.0.0",
    "status": "SUCCESS",
    "trained_at": "2026-09-05T06:12:00Z",
    "total_samples": 120,
    "metrics": {
      "roc_auc": 0.892,
      "pr_auc": 0.814,
      "f1_score": 0.750,
      "precision": 0.720,
      "recall": 0.783,
      "brier_score": 0.112,
      "confusion_matrix": [[18, 2], [1, 3]]
    },
    "top_global_features": [
      { "feature": "late_payment_count_3m", "importance": 0.352 },
      { "feature": "payment_status_trend", "importance": 0.281 },
      { "feature": "avg_payment_delay_days_3m", "importance": 0.185 }
    ],
    "is_active": true
  }
  ```

### 7.2 Metadata Model Churn Aktif: `GET /api/v1/ml/models/churn/metadata`
- **Response Body (`data`)**:
  ```json
  {
    "model_name": "churn_xgboost",
    "model_version": "1.0.0",
    "algorithm": "XGBClassifier",
    "trained_at": "2026-09-05T06:12:00Z",
    "features": [
      "tenure_months", "monthly_fee_current", "package_speed_mbps",
      "late_payment_count_3m", "late_payment_count_6m",
      "avg_payment_delay_days_3m", "payment_status_trend", "downgrade_flag_6m"
    ],
    "metrics": { "roc_auc": 0.892, "f1_score": 0.750 },
    "is_active": true
  }
  ```

### 7.3 Eksekusi Batch Inferensi: `POST /api/v1/ml/predictions/churn/batch`
- **Request Body**:
  ```json
  {
    "snapshot_date": "2026-09-05",
    "force_refresh": true
  }
  ```
- **Response Body (`data`)**:
  ```json
  {
    "snapshot_date": "2026-09-05",
    "model_version": "1.0.0",
    "total_evaluated": 120,
    "high_risk_count": 14,
    "medium_risk_count": 28,
    "low_risk_count": 78,
    "average_churn_probability": 0.245,
    "rows_saved": 120
  }
  ```

### 7.4 Daftar Pelanggan Risiko Tinggi: `GET /api/v1/ml/predictions/churn/high-risk`
- **Query Params**: `limit=20`, `min_probability=0.70`, `snapshot_date=2026-09-05`
- **Response Body (`data`)**:
  ```json
  [
    {
      "customer_id": 1013,
      "customer_name": "Customer #1013",
      "city": "Surabaya",
      "customer_status": "ACTIVE",
      "snapshot_date": "2026-09-05",
      "churn_probability": 0.842,
      "risk_level": "HIGH",
      "risk_tier_rank": 1,
      "top_risk_factors": [
        {
          "feature": "late_payment_count_3m",
          "impact": "INCREASES_RISK",
          "severity": "HIGH",
          "importance_weight": 0.35,
          "value": 2,
          "description": "2 kali tagihan terlambat dalam 3 bulan terakhir"
        },
        {
          "feature": "payment_status_trend",
          "impact": "INCREASES_RISK",
          "severity": "HIGH",
          "importance_weight": 0.28,
          "value": "WORSENING",
          "description": "Tren kedisiplinan pembayaran memburuk (WORSENING)"
        }
      ],
      "model_version": "1.0.0"
    }
  ]
  ```

### 7.5 Profil Risiko Pelanggan Individu: `GET /api/v1/ml/predictions/churn/customer/{customer_id}`
- **Path Parameter**: `customer_id` (integer)
- **Response Body (`data`)**: Mengembalikan objek `CustomerRiskProfile` untuk pelanggan terkait.

---

## 8. Mekanisme Sinkronisasi Otomatis (*Contract Drift Prevention*)

Untuk mencegah perbedaan antara dokumen kontrak ini dan kode aplikasi yang aktif:
1. **Automated OpenAPI Dump**: Backend menyertakan script `backend/scripts/export_openapi.py` yang dapat dieksekusi via terminal:
   ```bash
   python backend/scripts/export_openapi.py
   ```
   Script ini mengekstrak schema OpenAPI langsung dari runtime FastAPI dan menyimpannya ke `docs/openapi.json`.
2. **Contract Validation Test**: Test otomatis `backend/tests/integration/test_api_contract.py` memverifikasi kesesuaian response aktual dengan model Pydantic.
3. **Dokumentasi Swagger Interaktif**: Dapat diakses di browser pada `http://localhost:8000/docs` (Swagger UI) dan `http://localhost:8000/redoc` (ReDoc).
