# Mock ERP Database Environment (Data Engineering)

Direktori ini merepresentasikan **Sistem Database ERP Sumber (External Source System)** yang berdiri sendiri dan terpisah sepenuhnya dari sistem dashboard/feature store utama. Lingkungan ini dikelola layaknya sistem operasional ERP perusahaan ISP oleh tim Data Engineering untuk keperluan pengujian ekstraksi data nyata (*live query ingestion*).

---

## 1. Struktur Direktori

```
mock_erp_data_engineer/
├── README.md               # Dokumentasi sistem database mock ERP
├── docker-compose.yml      # Orkestrasi kontainer database ERP terisolasi
├── .env.example            # Template variabel lingkungan database
├── sql/
│   ├── 01_schema.sql       # DDL 21 tabel ISP MVP (sesuai spesifikasi DBML)
│   └── 02_seed.sql         # Seed dataset realistis ISP Indonesia & sinkronisasi sequence
└── scripts/
    └── verify_erp_db.py    # Skrip mandiri untuk audit ketersediaan tabel & jumlah baris
```

---

## 2. Spesifikasi Skema (21 Tabel DBML)

Database ini memuat 21 tabel operasional yang mencakup 7 modul domain bisnis:

1. **Organization & Access**: `department`, `employee`, `user_account`
2. **ISP Operations Master**: `internet_package`, `customer`, `customer_subscription`
3. **Procurement & Inventory**: `supplier`, `item`, `warehouse`, `stock`, `stock_ledger`, `purchase_order`, `purchase_order_item`, `purchase_invoice`, `purchase_payment`
4. **Billing & Sales**: `sales_invoice`, `sales_payment`
5. **Accounting (General Ledger)**: `account`, `journal_entry`, `journal_entry_line`
6. **Assets & Governance**: `asset`, `audit_log`

---

## 3. Cara Menjalankan

### A. Menyalakan Kontainer Database
Jalankan dari direktori ini:
```bash
docker compose up -d
```
Kontainer `erp_mock_source_db` akan:
1. Menjalankan image `postgres:16-alpine`.
2. Menjalankan file DDL `sql/01_schema.sql` dan seed `sql/02_seed.sql` secara otomatis saat inisialisasi volume pertama kali.
3. Terbuka pada port host **`5433`** (menghindari bentrok dengan port default PostgreSQL `5432`).
4. Bergabung ke Docker bridge network **`erp_shared_net`**.

### B. Verifikasi Ketersediaan Data
Gunakan skrip audit mandiri:
```bash
python scripts/verify_erp_db.py
# atau dengan URL kustom:
python scripts/verify_erp_db.py postgresql://erp_user:erp_secret_123@localhost:5433/isp_erp_db
```

### C. Mematikan Kontainer
```bash
docker compose down
# Atau hapus volume jika ingin reset data dari awal:
docker compose down -v
```

---

## 4. Parameter Koneksi (Connection String)

- **Akses dari Host Lokal (Python/Uvicorn/CLI)**:
  ```
  postgresql://erp_user:erp_secret_123@localhost:5433/isp_erp_db
  ```
- **Akses Lintas Kontainer Docker (antar network `erp_shared_net`)**:
  ```
  postgresql://erp_user:erp_secret_123@erp_mock_source_db:5432/isp_erp_db
  ```
