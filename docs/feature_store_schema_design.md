# Rancangan Feature Store Database — ISP Prediction & Decision Support System

Konteks: database ERP (skema ISP) berjalan di lokasi/infra data engineer, terpisah dari project Anda. Feature store ini adalah **database baru, milik project Anda sendiri**, diisi lewat job batch yang menembak query ke database sumber, bukan koneksi live/real-time. Karena sifatnya analitis (bukan operasional), granularitas refresh dirancang harian/mingguan/bulanan sesuai kebutuhan pola, bukan per-detik.

Stack yang dipakai: **PostgreSQL** (selaras dengan tech stack project — Postgres + pgvector).

---

## 1. Prinsip Desain

Empat prinsip yang jadi acuan setiap keputusan skema di bawah:

1. **Decoupled dari source** — feature store tidak pernah query langsung ke DB data engineer saat inference/dashboard load. Semua data sudah "ditarik" (extract) ke sini lewat job, sehingga source ERP tidak terbebani dan feature store bisa didesain ulang bebas tanpa menyentuh sistem operasional mereka.
2. **Point-in-time correct** — setiap baris fitur punya `snapshot_date`/`event_date` eksplisit. Ini wajib karena target prediksi (churn, cash flow) itu time-dependent; kalau fitur diambil dari "state terkini" tanpa jejak waktu, model akan bocor informasi masa depan (data leakage) saat training.
3. **Snapshot > realtime** — feature store diisi lewat *periodic snapshot fact tables*, bukan streaming/CDC. Selaras dengan yang Anda sebut: insight butuh pola, bukan reaksi per detik.
4. **ML-ready + BI-ready sekaligus** — layer paling atas (`feature_*`) adalah tabel lebar (wide, denormalized) siap di-`SELECT *` ke pandas/XGBoost, sementara layer fact/dimensi di bawahnya tetap ternormalisasi cukup untuk dashboard/BI query fleksibel.

Struktur layer:

```
[ERP Source DB]  --(query job, incremental)-->  [staging]  -->  [dimension + fact snapshot]  -->  [feature_* (ML-ready)]
                                                                                                  -->  [label_* (untuk training)]
```

---

## 2. Strategi Query Ekstraksi dari ERP Source

Karena Anda menembak query ke DB data engineer (bukan CDC/replication), pakai pola **incremental extraction pakai watermark** di `updated_at` / `created_at`, dijalankan oleh scheduler (Airflow/Dagster/cron + script Python/TS) dengan tabel log untuk menyimpan watermark terakhir per tabel.

Contoh query per domain (dijalankan read-only ke source DB):

```sql
-- Domain: Subscription & Customer (untuk fitur churn)
SELECT id, customer_id, package_id, subscription_no, start_date, end_date,
       monthly_fee, billing_day, status, created_at, updated_at
FROM customer_subscription
WHERE updated_at > :last_watermark
  AND updated_at <= :batch_cutoff;

-- Domain: Billing (untuk fitur payment behavior & cash flow)
SELECT id, customer_subscription_id, invoice_number, invoice_period, invoice_date,
       due_date, total_amount, payment_status, updated_at
FROM sales_invoice
WHERE updated_at > :last_watermark AND updated_at <= :batch_cutoff;

SELECT id, sales_invoice_id, payment_date, amount, payment_status, created_at
FROM sales_payment
WHERE created_at > :last_watermark AND created_at <= :batch_cutoff;

-- Domain: Accounting (untuk cash flow keseluruhan)
SELECT je.entry_date, jel.account_id, a.account_type, jel.debit, jel.credit
FROM journal_entry je
JOIN journal_entry_line jel ON jel.journal_entry_id = je.id
JOIN account a ON a.id = jel.account_id
WHERE je.entry_date > :last_watermark_date AND je.entry_date <= :batch_cutoff_date;

-- Domain: Inventory (opsional, untuk fitur operasional/risiko layanan)
SELECT warehouse_id, item_id, quantity, last_updated
FROM stock
WHERE last_updated > :last_watermark;
```

**Catatan penting:** tabel `stock_ledger`, `purchase_*`, dan `journal_entry*` bersifat append-only (jarang di-update), jadi lebih aman diekstrak pakai `created_at`/`entry_date` sebagai watermark, bukan `updated_at`. Tabel seperti `customer_subscription` dan `sales_invoice` sifatnya mutable (status berubah), jadi `updated_at` wajib jadi watermark utama agar perubahan status tertangkap.

---

## 3. Skema Database Feature Store (DDL PostgreSQL)

### 3.1 Staging Layer (opsional tapi direkomendasikan)

Tabel cermin 1:1 dari hasil extract, sebelum diolah — memudahkan replay/debug tanpa perlu query ulang ke source.

```sql
CREATE SCHEMA IF NOT EXISTS staging;

CREATE TABLE staging.stg_customer_subscription (
    source_id          integer NOT NULL,
    customer_id         integer,
    package_id          integer,
    subscription_no     varchar,
    start_date          date,
    end_date            date,
    monthly_fee         numeric,
    billing_day         integer,
    status               varchar,
    source_updated_at   timestamp,
    batch_id             uuid NOT NULL,
    loaded_at             timestamp DEFAULT now()
);
-- pola yang sama diulang untuk stg_sales_invoice, stg_sales_payment,
-- stg_journal_entry_line, stg_stock, dst.
```

### 3.2 Dimension Tables (SCD Type 2 untuk yang berubah pelan)

Dimensi pakai *Slowly Changing Dimension Type 2* khusus untuk atribut yang bisa berubah dan histori perubahannya penting untuk fitur (mis. status pelanggan, kota, paket).

```sql
CREATE SCHEMA IF NOT EXISTS feature_store;

CREATE TABLE feature_store.dim_customer (
    customer_key    bigserial PRIMARY KEY,      -- surrogate key
    customer_id     integer NOT NULL,           -- natural key dari source
    customer_name   varchar,
    city             varchar,
    installation_date date,
    status            varchar,                    -- ACTIVE / SUSPENDED / TERMINATED, dst
    valid_from        date NOT NULL,
    valid_to          date,                        -- null = versi aktif saat ini
    is_current        boolean DEFAULT true,
    source_updated_at timestamp
);
CREATE INDEX idx_dim_customer_natural ON feature_store.dim_customer (customer_id, is_current);

CREATE TABLE feature_store.dim_package (
    package_key     bigserial PRIMARY KEY,
    package_id      integer NOT NULL,
    package_name    varchar,
    speed_mbps      integer,
    monthly_price   numeric,
    valid_from      date NOT NULL,
    valid_to        date,
    is_current      boolean DEFAULT true
);

CREATE TABLE feature_store.dim_date (
    date_key        date PRIMARY KEY,
    year            integer,
    month           integer,
    quarter         integer,
    week_of_year    integer,
    day_of_week     integer,
    is_month_end    boolean,
    is_billing_cycle_end boolean
);
```

### 3.3 Fact / Snapshot Tables (Point-in-Time)

*Periodic snapshot fact* — satu baris per entitas per titik waktu (bukan per transaksi), ini yang bikin fitur "point-in-time correct".

```sql
-- Snapshot bulanan status & perilaku langganan per pelanggan
CREATE TABLE feature_store.fact_subscription_snapshot (
    snapshot_date       date NOT NULL,
    customer_key        bigint REFERENCES feature_store.dim_customer(customer_key),
    package_key          bigint REFERENCES feature_store.dim_package(package_key),
    subscription_status  varchar,
    tenure_days           integer,           -- umur langganan pada snapshot_date
    monthly_fee            numeric,
    is_active               boolean,
    batch_id                 uuid NOT NULL,
    PRIMARY KEY (snapshot_date, customer_key)
) PARTITION BY RANGE (snapshot_date);

-- Snapshot bulanan billing & payment behavior per pelanggan
CREATE TABLE feature_store.fact_billing_monthly (
    invoice_period       date NOT NULL,       -- periode tagihan (bulan)
    customer_key         bigint REFERENCES feature_store.dim_customer(customer_key),
    invoiced_amount        numeric,
    paid_amount             numeric,
    payment_status           varchar,
    days_late                 integer,          -- null jika belum lunas / tidak telat
    batch_id                   uuid NOT NULL,
    PRIMARY KEY (invoice_period, customer_key)
);

-- Snapshot bulanan cash flow perusahaan (agregat, dari accounting)
CREATE TABLE feature_store.fact_cashflow_monthly (
    period_month           date NOT NULL,      -- selalu tanggal 1 di bulan tsb
    total_revenue            numeric,
    total_expense             numeric,
    accounts_receivable        numeric,
    accounts_payable            numeric,
    net_cashflow                  numeric,
    batch_id                        uuid NOT NULL,
    PRIMARY KEY (period_month)
);

-- Snapshot mingguan inventaris (opsional, untuk fitur risiko operasional/instalasi)
CREATE TABLE feature_store.fact_inventory_snapshot (
    snapshot_date         date NOT NULL,
    warehouse_id            integer,
    item_id                    integer,
    quantity_on_hand           integer,
    batch_id                     uuid NOT NULL,
    PRIMARY KEY (snapshot_date, warehouse_id, item_id)
);
```

### 3.4 ML-Ready Feature Tables

Tabel lebar, satu baris per entitas per `snapshot_date`, langsung siap `SELECT *` untuk training/inference — hasil agregasi dari fact tables di atas (dihitung oleh job, bukan query real-time).

```sql
CREATE TABLE feature_store.feature_customer_churn (
    snapshot_date                date NOT NULL,
    customer_id                    integer NOT NULL,
    tenure_months                    numeric,
    monthly_fee_current                numeric,
    package_speed_mbps                    integer,
    late_payment_count_3m                   integer,
    late_payment_count_6m                     integer,
    avg_payment_delay_days_3m                   numeric,
    payment_status_trend                          varchar,   -- IMPROVING / STABLE / WORSENING
    downgrade_flag_6m                               boolean,
    batch_id                                          uuid NOT NULL,
    PRIMARY KEY (snapshot_date, customer_id)
);

CREATE TABLE feature_store.feature_cashflow_forecast (
    snapshot_date            date NOT NULL,   -- bulanan
    total_revenue_current       numeric,
    total_expense_current         numeric,
    net_cashflow_current             numeric,
    revenue_trend_3m                    numeric,   -- slope/perubahan 3 bulan terakhir
    ar_aging_30                            numeric,
    ar_aging_60                              numeric,
    ar_aging_90plus                            numeric,
    batch_id                                     uuid NOT NULL,
    PRIMARY KEY (snapshot_date)
);
```

### 3.5 Label Table (Anti-Leakage, Wajib untuk Supervised Learning)

Dipisah dari tabel fitur secara sengaja, supaya window observasi label tidak pernah tercampur dengan window fitur saat training.

```sql
CREATE TABLE feature_store.label_churn_event (
    customer_id             integer NOT NULL,
    feature_snapshot_date     date NOT NULL,     -- fitur diambil per tanggal ini
    label_window_start          date NOT NULL,   -- mulai observasi churn (setelah snapshot)
    label_window_end              date NOT NULL,
    churned                          boolean,
    churn_date                        date,
    PRIMARY KEY (customer_id, feature_snapshot_date)
);
```

### 3.6 Metadata & Orchestration Tables

```sql
CREATE TABLE feature_store.etl_batch_log (
    batch_id            uuid PRIMARY KEY,
    source_table          varchar NOT NULL,
    watermark_start          timestamp,
    watermark_end              timestamp,
    row_count                    integer,
    status                          varchar,   -- SUCCESS / FAILED / PARTIAL
    started_at                        timestamp,
    finished_at                          timestamp
);

CREATE TABLE feature_store.data_quality_log (
    id                bigserial PRIMARY KEY,
    batch_id            uuid REFERENCES feature_store.etl_batch_log(batch_id),
    check_name            varchar,   -- e.g. 'null_check_customer_id', 'fk_integrity_subscription'
    table_name              varchar,
    status                      varchar,   -- PASS / FAIL / WARN
    details                        text,
    checked_at                       timestamp DEFAULT now()
);
```

---

## 4. Refresh Cadence & Job Scheduling

Disesuaikan per domain, bukan disamaratakan — sesuai prinsip "insight butuh pola, bukan reaksi per detik":

| Domain | Job Frequency | Alasan |
|---|---|---|
| `fact_subscription_snapshot` | Harian (incremental) → snapshot final tiap akhir hari | Status langganan bisa berubah kapan saja, tapi feature churn biasanya dikonsumsi mingguan/bulanan |
| `fact_billing_monthly` | Bulanan, dipicu setelah `billing_day` tiap siklus | Selaras dengan siklus tagihan ISP, tidak ada gunanya lebih sering |
| `fact_cashflow_monthly` | Bulanan, setelah tutup buku (end of month) | Cash flow accounting secara alami bulanan |
| `fact_inventory_snapshot` | Mingguan | Cukup untuk mendeteksi tren stok tanpa membebani job harian |
| `feature_customer_churn` | Mingguan (dihitung dari snapshot harian yg diagregasi) | Model churn biasanya di-refresh mingguan, bukan harian |
| `feature_cashflow_forecast` | Bulanan | Mengikuti siklus `fact_cashflow_monthly` |

Semua job **idempotent**: pakai `INSERT ... ON CONFLICT (snapshot_date, customer_key) DO UPDATE`, sehingga job yang di-rerun tidak menghasilkan duplikat atau data ganda.

---

## 5. Konvensi Penamaan & Kolom Metadata Wajib

Supaya konsisten dan gampang di-trace ke source:

- Prefix tabel: `stg_` (staging), `dim_` (dimensi), `fact_` (snapshot fact), `feature_` (ML-ready), `label_` (target training).
- Setiap tabel fact/feature **wajib** punya: `snapshot_date` (atau `invoice_period`/`period_month` sesuai granularitas), dan `batch_id` (untuk traceability ke `etl_batch_log`).
- Surrogate key dimensi diberi suffix `_key` (mis. `customer_key`), sedangkan natural key dari source tetap disimpan sebagai `_id` (mis. `customer_id`) supaya bisa di-join balik ke ERP kalau perlu audit.

---

## 6. Indexing & Partitioning

- **Partition `fact_subscription_snapshot`** (dan tabel fact snapshot besar lain) secara `RANGE (snapshot_date)` per bulan — mempercepat query dashboard yang biasanya filter per rentang waktu, dan memudahkan drop/archive partisi lama.
- Index komposit `(customer_id, snapshot_date)` pada semua `feature_*` untuk lookup cepat saat inference per-customer.
- Index pada `dim_customer(customer_id, is_current)` untuk mempercepat resolve surrogate key terbaru saat proses load fact table.

---

## 7. Gap yang Perlu Dikonfirmasi ke Data Engineer

Dari skema ERP yang Anda kirim, beberapa hal belum tersedia langsung untuk domain "service" yang disebut di arsitektur pipeline Anda:

- **Tidak ada tabel tiket/keluhan layanan** (support ticket, gangguan jaringan, dsb) di skema yang diberikan — padahal ini biasanya sinyal churn yang kuat. Perlu ditanyakan apakah ada sistem terpisah untuk ini.
- **Tidak ada histori perubahan status eksplisit** (mis. audit trail kapan `customer.status` berubah dari ACTIVE ke SUSPENDED) — skema hanya simpan status terkini di `customer` dan `customer_subscription`. Ini yang membuat SCD Type 2 di sisi feature store jadi penting: perubahan status baru bisa "tertangkap sebagai histori" mulai dari saat Anda mulai menjalankan job, bukan mundur ke masa lalu — kecuali data engineer bisa berikan histori/log tambahan (mis. dari `audit_log`).

---

## 8. Next Steps

1. Konfirmasi mekanisme akses ke DB data engineer (koneksi langsung read-only vs export terjadwal/CSV-Parquet).
2. Bangun job extraction (Python/TS) untuk domain subscription & billing dulu — dua domain ini paling langsung dipakai untuk fitur churn.
3. Implementasikan `etl_batch_log` dan `data_quality_log` di awal, sebelum fact/feature table diisi — supaya dari batch pertama sudah ada observability.
4. Setelah feature store domain subscription+billing jalan, baru perluas ke domain accounting (cash flow) dan inventory.
