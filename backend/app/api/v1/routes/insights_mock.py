from datetime import datetime, timezone
from typing import Dict, Optional
from fastapi import APIRouter, Depends, Path, Query, Request, status

from app.core.exceptions import EntityNotFoundError
from app.core.security import get_current_user
from app.schemas.envelope import ResponseEnvelope, success_response
from app.schemas.insights import InsightPackage

router = APIRouter(prefix="/insights", tags=["Insights (Mock Prototype)"])

# Rich mock data repository for each business module
MOCK_MODULE_INSIGHTS: Dict[str, dict] = {
    "commercial": {
        "module": "commercial",
        "as_of_date": "2026-09-01",
        "executive_summary": "Tingkat churn pelanggan segmen ritel diproyeksikan meningkat 2.4% pada kuartal mendatang akibat keterlambatan pembayaran berulang pasca kenaikan tarif.",
        "key_metrics": [
            {
                "key": "mrr",
                "label": "Monthly Recurring Revenue",
                "value": 1450000000.0,
                "formatted_value": "Rp 1,45 M",
                "unit": "IDR",
                "change_percentage": 3.2,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "high_churn_risk",
                "label": "Pelanggan Risiko Tinggi",
                "value": 142.0,
                "formatted_value": "142 Pelanggan",
                "unit": "customers",
                "change_percentage": 12.5,
                "trend": "up",
                "status": "critical",
            },
            {
                "key": "arpu",
                "label": "Average Revenue Per User",
                "value": 385000.0,
                "formatted_value": "Rp 385 rb",
                "unit": "IDR",
                "change_percentage": -1.2,
                "trend": "down",
                "status": "warning",
            },
        ],
        "narrative_insights": [
            {
                "id": "ins-comm-001",
                "domain": "commercial",
                "severity": "critical",
                "title": "Konsentrasi Risiko Churn pada Paket 50 Mbps",
                "narrative": "Model XGBoost mendeteksi 68 pelanggan paket 50 Mbps mengalami keterlambatan pembayaran >15 hari selama 2 bulan berturut-turut setelah penyesuaian tarif.",
                "suggested_actions": [
                    "Kirimkan notifikasi penawaran diskon perpanjangan kontrak tahunan otomatis.",
                    "Prioritaskan tim customer retention untuk menghubungi 20 akun berbobot tagihan tertinggi.",
                ],
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
                        "x": {"field": "risk_tier", "type": "nominal", "axis": {"title": "Tingkat Risiko"}},
                        "y": {"field": "count", "type": "quantitative", "axis": {"title": "Jumlah Pelanggan"}},
                        "color": {
                            "field": "risk_tier",
                            "type": "nominal",
                            "scale": {
                                "domain": ["Rendah", "Sedang", "Tinggi"],
                                "range": ["#22c55e", "#eab308", "#ef4444"],
                            },
                        },
                    },
                    "data": {
                        "values": [
                            {"risk_tier": "Rendah", "count": 1250},
                            {"risk_tier": "Sedang", "count": 340},
                            {"risk_tier": "Tinggi", "count": 142},
                        ]
                    },
                },
                "data": [
                    {"risk_tier": "Rendah", "count": 1250},
                    {"risk_tier": "Sedang", "count": 340},
                    {"risk_tier": "Tinggi", "count": 142},
                ],
            }
        ],
        "audit_table": {
            "title": "Audit Portofolio Risiko Pelanggan (XGBoost Churn Profiling)",
            "description": "Daftar akun pelanggan, estimasi probabilitas churn, dan pendorong risiko utama",
            "columns": [
                {"key": "customer_id", "label": "ID Akun", "type": "text"},
                {"key": "customer_name", "label": "Nama Pelanggan", "type": "text"},
                {"key": "city", "label": "Kota", "type": "text"},
                {"key": "churn_probability", "label": "Probabilitas Churn", "type": "percentage"},
                {"key": "risk_level", "label": "Tingkat Risiko", "type": "badge"},
                {"key": "primary_risk_driver", "label": "Faktor Pendorong Risiko", "type": "text"},
            ],
            "rows": [
                {"customer_id": "CUST-1013", "customer_name": "Customer #1013", "city": "Surabaya", "churn_probability": "84.2%", "risk_level": "HIGH", "primary_risk_driver": "Keterlambatan bayar >=2x (3 bln)"},
                {"customer_id": "CUST-1045", "customer_name": "Customer #1045", "city": "Bandung", "churn_probability": "76.5%", "risk_level": "HIGH", "primary_risk_driver": "Status pembayaran WORSENING"},
                {"customer_id": "CUST-1088", "customer_name": "Customer #1088", "city": "Jakarta", "churn_probability": "71.0%", "risk_level": "HIGH", "primary_risk_driver": "Downgrade paket 6 bulan terakhir"},
            ],
            "total_records": 3,
        },
        "model_metadata": [
            {
                "model_name": "xgboost_churn_v1",
                "version": "1.0.0",
                "prediction_window": "30_days",
                "confidence_score": 0.892,
                "last_trained_at": "2026-08-28T03:00:00Z",
            }
        ],
    },
    "finance": {
        "module": "finance",
        "as_of_date": "2026-09-01",
        "executive_summary": "Arus kas operasional bulan berjalan diproyeksikan surplus Rp 320 Juta dengan penurunan piutang tak tertagih (AR Aging >60 hari) sebesar 4.1%.",
        "key_metrics": [
            {
                "key": "net_cashflow",
                "label": "Net Cash Flow Proyeksi",
                "value": 320000000.0,
                "formatted_value": "Rp 320 Jt",
                "unit": "IDR",
                "change_percentage": 5.4,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "total_ar_outstanding",
                "label": "Total Piutang Berjalan (AR)",
                "value": 245000000.0,
                "formatted_value": "Rp 245 Jt",
                "unit": "IDR",
                "change_percentage": -4.1,
                "trend": "down",
                "status": "good",
            },
        ],
        "narrative_insights": [
            {
                "id": "ins-fin-001",
                "domain": "finance",
                "severity": "warning",
                "title": "Lonjakan Piutang Segmen Korporat Area Surabaya",
                "narrative": "Tiga klien korporat dengan total nilai tagihan Rp 85 Juta terlambat membayar melampaui batas jatuh tempo (Term of Payment 30 hari).",
                "suggested_actions": [
                    "Terbitkan Surat Peringatan 1 (SP1) otomatis melalui sistem penagihan.",
                    "Jadwalkan rekonsiliasi faktur dengan manajer keuangan klien bersangkutan.",
                ],
            }
        ],
        "visualizations": [
            {
                "chart_id": "chart-ar-aging",
                "title": "Komposisi AR Aging (Umur Piutang)",
                "description": "Distribusi nominal piutang berdasarkan rentang keterlambatan",
                "chart_library": "vega-lite",
                "spec": {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "mark": "arc",
                    "encoding": {
                        "theta": {"field": "amount", "type": "quantitative"},
                        "color": {"field": "bucket", "type": "nominal"},
                    },
                    "data": {
                        "values": [
                            {"bucket": "0-30 Hari", "amount": 160000000},
                            {"bucket": "31-60 Hari", "amount": 55000000},
                            {"bucket": ">60 Hari", "amount": 30000000},
                        ]
                    },
                },
                "data": [
                    {"bucket": "0-30 Hari", "amount": 160000000},
                    {"bucket": "31-60 Hari", "amount": 55000000},
                    {"bucket": ">60 Hari", "amount": 30000000},
                ],
            }
        ],
        "audit_table": {
            "title": "Audit Faktur Piutang Berjalan & Jatuh Tempo (AR Ledger)",
            "description": "Rincian faktur pelanggan korporat dan ritel dengan status penagihan aktif",
            "columns": [
                {"key": "invoice_id", "label": "No. Faktur", "type": "text"},
                {"key": "client_name", "label": "Nama Klien / Pelanggan", "type": "text"},
                {"key": "due_date", "label": "Tgl Jatuh Tempo", "type": "date"},
                {"key": "amount", "label": "Nominal Tagihan", "type": "currency"},
                {"key": "days_overdue", "label": "Keterlambatan", "type": "text"},
                {"key": "bucket", "label": "Bucket Aging", "type": "badge"},
                {"key": "status", "label": "Status", "type": "badge"},
            ],
            "rows": [
                {"invoice_id": "INV-2026-0881", "client_name": "PT Surya Mandiri Logistik", "due_date": "2026-08-15", "amount": 45000000.0, "days_overdue": "21 Hari", "bucket": "0-30 Hari", "status": "SP1 Terbit"},
                {"invoice_id": "INV-2026-0842", "client_name": "CV Prima Jaya Abadi", "due_date": "2026-07-28", "amount": 28000000.0, "days_overdue": "39 Hari", "bucket": "31-60 Hari", "status": "Mediasi"},
                {"invoice_id": "INV-2026-0790", "client_name": "PT Nusantara Digital Hub", "due_date": "2026-06-30", "amount": 30000000.0, "days_overdue": "67 Hari", "bucket": ">60 Hari", "status": "Kritis"},
            ],
            "total_records": 3,
        },
        "model_metadata": [
            {
                "model_name": "prophet_cashflow_v1",
                "version": "1.0.0",
                "prediction_window": "90_days",
                "confidence_score": 0.865,
                "last_trained_at": "2026-08-31T20:00:00Z",
            }
        ],
    },
    "procurement": {
        "module": "procurement",
        "as_of_date": "2026-09-01",
        "executive_summary": "Lead time pengadaan kabel optik impor mengalami deviasi +6 hari kerja akibat kendala pengiriman logistik vendor utama.",
        "key_metrics": [
            {
                "key": "avg_lead_time",
                "label": "Rata-rata Lead Time PO",
                "value": 18.2,
                "formatted_value": "18.2 Hari",
                "unit": "days",
                "change_percentage": 14.0,
                "trend": "up",
                "status": "warning",
            },
            {
                "key": "vendor_risk_count",
                "label": "Vendor Skor Risiko Tinggi",
                "value": 2.0,
                "formatted_value": "2 Vendor",
                "unit": "vendors",
                "change_percentage": 0.0,
                "trend": "neutral",
                "status": "warning",
            },
        ],
        "narrative_insights": [
            {
                "id": "ins-proc-001",
                "domain": "procurement",
                "severity": "warning",
                "title": "Keterlambatan Pasokan ONT dari PT Telko Supply",
                "narrative": "Pemesanan 500 unit ONT dual-band telah melewati estimasi pengiriman 7 hari, berisiko menunda instalasi pelanggan baru cluster BSD.",
                "suggested_actions": [
                    "Alihkan sebagian PO ke vendor alternatif (PT Mitra Jaringan).",
                    "Terapkan denda penalti keterlambatan sesuai klausul kontrak pengadaan.",
                ],
            }
        ],
        "visualizations": [
            {
                "chart_id": "chart-vendor-performance",
                "title": "Skor Pemenuhan Waktu Vendor Utama",
                "description": "Persentase On-Time Delivery per vendor kuartal ini",
                "chart_library": "vega-lite",
                "spec": {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "vendor", "type": "nominal", "axis": {"title": "Vendor"}},
                        "y": {"field": "score", "type": "quantitative", "axis": {"title": "Skor OTD (%)"}},
                    },
                    "data": {
                        "values": [
                            {"vendor": "PT Optik Nusantara", "score": 94},
                            {"vendor": "PT Telko Supply", "score": 68},
                            {"vendor": "PT Router Mandiri", "score": 88},
                        ]
                    },
                },
                "data": [
                    {"vendor": "PT Optik Nusantara", "score": 94},
                    {"vendor": "PT Telko Supply", "score": 68},
                    {"vendor": "PT Router Mandiri", "score": 88},
                ],
            }
        ],
        "audit_table": {
            "title": "Audit Pemesanan Pembelian (Purchase Orders) & Kinerja Vendor",
            "description": "Daftar PO berjalan, estimasi kedatangan, dan deviasi pemenuhan waktu vendor",
            "columns": [
                {"key": "po_number", "label": "No. PO", "type": "text"},
                {"key": "vendor_name", "label": "Nama Vendor", "type": "text"},
                {"key": "item_category", "label": "Item Pengadaan", "type": "text"},
                {"key": "po_value", "label": "Nilai PO", "type": "currency"},
                {"key": "promised_delivery", "label": "Target Tiba", "type": "date"},
                {"key": "delay_days", "label": "Deviasi", "type": "text"},
                {"key": "otd_status", "label": "Status OTD", "type": "badge"},
            ],
            "rows": [
                {"po_number": "PO-2026-0412", "vendor_name": "PT Optik Nusantara", "item_category": "Drop Cable 1 Core (20 km)", "po_value": 78000000.0, "promised_delivery": "2026-09-02", "delay_days": "0 Hari", "otd_status": "Tepat Waktu"},
                {"po_number": "PO-2026-0398", "vendor_name": "PT Telko Supply", "item_category": "ONT XPON Dual-Band (500 unit)", "po_value": 145000000.0, "promised_delivery": "2026-08-28", "delay_days": "+7 Hari", "otd_status": "Terlambat"},
            ],
            "total_records": 2,
        },
        "model_metadata": [
            {
                "model_name": "vendor_lead_time_xgb",
                "version": "1.0.0",
                "prediction_window": "30_days",
                "confidence_score": 0.812,
                "last_trained_at": "2026-08-25T12:00:00Z",
            }
        ],
    },
    "inventory": {
        "module": "inventory",
        "as_of_date": "2026-09-01",
        "executive_summary": "Stok kabel drop optik 1 core di Gudang Utama Jakarta menipis dan diprediksi habis dalam 11 hari kerja jika laju instalasi tetap.",
        "key_metrics": [
            {
                "key": "stockout_risk_items",
                "label": "Item Berisiko Stockout",
                "value": 3.0,
                "formatted_value": "3 SKU",
                "unit": "items",
                "change_percentage": 50.0,
                "trend": "up",
                "status": "critical",
            },
            {
                "key": "inventory_value",
                "label": "Total Nilai Aset Gudang",
                "value": 680000000.0,
                "formatted_value": "Rp 680 Jt",
                "unit": "IDR",
                "change_percentage": -2.5,
                "trend": "down",
                "status": "good",
            },
        ],
        "narrative_insights": [
            {
                "id": "ins-inv-001",
                "domain": "inventory",
                "severity": "critical",
                "title": "Risiko Kehabisan Drop Cable 1 Core",
                "narrative": "Laju pemakaian drop cable meningkat 35% karena percepatan aktivasi program 'Merdeka Internet'. Sisa stok 4.200 meter.",
                "suggested_actions": [
                    "Lakukan Purchase Request (PR) darurat sebanyak 15.000 meter kabel.",
                    "Lakukan transfer stok sementara dari Gudang Cabang Bandung (tersedia surplus 8.000 meter).",
                ],
            }
        ],
        "visualizations": [
            {
                "chart_id": "chart-stock-depletion",
                "title": "Proyeksi Penurunan Stok Material Kritis",
                "description": "Tren konsumsi material vs batas safety stock",
                "chart_library": "vega-lite",
                "spec": {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "mark": "line",
                    "encoding": {
                        "x": {"field": "day", "type": "ordinal", "axis": {"title": "Hari ke Depan"}},
                        "y": {"field": "remaining_stock", "type": "quantitative", "axis": {"title": "Sisa Stok (m)"}},
                    },
                    "data": {
                        "values": [
                            {"day": "Hari 1", "remaining_stock": 4200},
                            {"day": "Hari 5", "remaining_stock": 2800},
                            {"day": "Hari 10", "remaining_stock": 800},
                            {"day": "Hari 15", "remaining_stock": 0},
                        ]
                    },
                },
                "data": [
                    {"day": "Hari 1", "remaining_stock": 4200},
                    {"day": "Hari 5", "remaining_stock": 2800},
                    {"day": "Hari 10", "remaining_stock": 800},
                    {"day": "Hari 15", "remaining_stock": 0},
                ],
            }
        ],
        "audit_table": {
            "title": "Audit Saldo Gudang & Ketahanan Stok Material Jaringan",
            "description": "Pemantauan posisi stok aktual material, batas safety stock, dan proyeksi hari habis",
            "columns": [
                {"key": "sku", "label": "Kode SKU", "type": "text"},
                {"key": "item_name", "label": "Nama Material", "type": "text"},
                {"key": "warehouse", "label": "Lokasi Gudang", "type": "text"},
                {"key": "stock_qty", "label": "Stok Aktual", "type": "number"},
                {"key": "safety_stock", "label": "Safety Stock", "type": "number"},
                {"key": "runway_days", "label": "Ketahanan (Hari)", "type": "number"},
                {"key": "risk_level", "label": "Tingkat Risiko", "type": "badge"},
            ],
            "rows": [
                {"sku": "MAT-CBL-001", "item_name": "Drop Cable 1 Core 1000m", "warehouse": "Gudang Utama Jakarta", "stock_qty": 4200, "safety_stock": 1500, "runway_days": 11, "risk_level": "Kritis"},
                {"sku": "MAT-ONT-004", "item_name": "ONT XPON Dual-Band AC1200", "warehouse": "Gudang Utama Jakarta", "stock_qty": 65, "safety_stock": 50, "runway_days": 8, "risk_level": "Kritis"},
            ],
            "total_records": 2,
        },
        "model_metadata": [
            {
                "model_name": "stockout_forecast_v1",
                "version": "1.0.0",
                "prediction_window": "14_days",
                "confidence_score": 0.884,
                "last_trained_at": "2026-08-30T00:00:00Z",
            }
        ],
    },
    "asset": {
        "module": "asset",
        "as_of_date": "2026-09-01",
        "executive_summary": "14 unit OLT di 3 POP distribusi utama memerlukan pemeliharaan preventif dalam 30 hari untuk mencegah overheat jelang musim hujan.",
        "key_metrics": [
            {
                "key": "assets_needing_maintenance",
                "label": "Aset Perlu Servis",
                "value": 14.0,
                "formatted_value": "14 Unit",
                "unit": "units",
                "change_percentage": 16.7,
                "trend": "up",
                "status": "warning",
            },
            {
                "key": "healthy_asset_ratio",
                "label": "Rasio Kesehatan Aset",
                "value": 96.2,
                "formatted_value": "96.2%",
                "unit": "%",
                "change_percentage": -0.5,
                "trend": "down",
                "status": "good",
            },
        ],
        "narrative_insights": [
            {
                "id": "ins-ast-001",
                "domain": "asset",
                "severity": "warning",
                "title": "Kenaikan Suhu Operasional OLT POP Rawamangun",
                "narrative": "Sensor suhu mendeteksi rata-rata 58°C (ambang normal 50°C) selama 7 hari berturut-turut, diindikasikan filter pendingin pendingin udara POP tersumbat debu.",
                "suggested_actions": [
                    "Jadwalkan tim teknisi ME untuk inspeksi AC dan pembersihan filter POP Rawamangun.",
                    "Lakukan pengecekan redundancy power supply.",
                ],
            }
        ],
        "visualizations": [
            {
                "chart_id": "chart-asset-health",
                "title": "Distribusi Kondisi Aset Jaringan",
                "description": "Kondisi operasional router dan switch distribusi",
                "chart_library": "vega-lite",
                "spec": {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "status", "type": "nominal"},
                        "y": {"field": "count", "type": "quantitative"},
                    },
                    "data": {
                        "values": [
                            {"status": "Prima", "count": 240},
                            {"status": "Perlu Pemeliharaan", "count": 14},
                            {"status": "Kritis", "count": 2},
                        ]
                    },
                },
                "data": [
                    {"status": "Prima", "count": 240},
                    {"status": "Perlu Pemeliharaan", "count": 14},
                    {"status": "Kritis", "count": 2},
                ],
            }
        ],
        "audit_table": {
            "title": "Audit Kondisi Aset Jaringan & Status Pemeliharaan",
            "description": "Daftar perangkat router core, switch distribusi, dan OLT di seluruh Point of Presence (POP)",
            "columns": [
                {"key": "asset_id", "label": "Asset Tag", "type": "text"},
                {"key": "device_name", "label": "Tipe Perangkat", "type": "text"},
                {"key": "location", "label": "Lokasi / POP", "type": "text"},
                {"key": "operating_temp", "label": "Suhu (°C)", "type": "text"},
                {"key": "condition", "label": "Kondisi", "type": "badge"},
                {"key": "last_serviced", "label": "Servis Terakhir", "type": "date"},
                {"key": "action_needed", "label": "Rekomendasi Aksi", "type": "text"},
            ],
            "rows": [
                {"asset_id": "AST-OLT-014", "device_name": "Huawei SmartAX MA5800-X7", "location": "POP Rawamangun", "operating_temp": "58°C", "condition": "Perlu Pemeliharaan", "last_serviced": "2026-03-10", "action_needed": "Pembersihan filter & cek pendingin"},
            ],
            "total_records": 1,
        },
        "model_metadata": [
            {
                "model_name": "predictive_maintenance_rf",
                "version": "1.0.0",
                "prediction_window": "30_days",
                "confidence_score": 0.871,
                "last_trained_at": "2026-08-20T10:00:00Z",
            }
        ],
    },
    "service": {
        "module": "service",
        "as_of_date": "2026-09-01",
        "executive_summary": "Tingkat pemenuhan SLA penanganan tiket gangguan mencapai 94.8%, melampaui target korporat 92.0%. Waktu perbaikan rata-rata (MTTR) adalah 2.4 jam.",
        "key_metrics": [
            {
                "key": "sla_compliance",
                "label": "Pencapaian SLA Tiket",
                "value": 94.8,
                "formatted_value": "94.8%",
                "unit": "%",
                "change_percentage": 2.1,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "avg_mttr",
                "label": "Mean Time to Resolve (MTTR)",
                "value": 2.4,
                "formatted_value": "2.4 Jam",
                "unit": "hours",
                "change_percentage": -15.0,
                "trend": "down",
                "status": "good",
            },
        ],
        "narrative_insights": [
            {
                "id": "ins-srv-001",
                "domain": "service",
                "severity": "info",
                "title": "Penurunan Signifikan Gangguan Fiber Cut Area Selatan",
                "narrative": "Pemasangan proteksi jalur kabel bawah tanah baru berhasil memangkas frekuensi fiber cut sebesar 60% dibanding bulan lalu.",
                "suggested_actions": [
                    "Perluas implementasi proteksi armor conduit pada jalur trunk rute timur.",
                ],
            }
        ],
        "visualizations": [
            {
                "chart_id": "chart-ticket-sla",
                "title": "Tren Penyelesaian Tiket per Kategori",
                "description": "Proporsi tiket diselesaikan dalam batas SLA vs SLA Breach",
                "chart_library": "vega-lite",
                "spec": {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "category", "type": "nominal"},
                        "y": {"field": "count", "type": "quantitative"},
                        "color": {"field": "sla_status", "type": "nominal"},
                    },
                    "data": {
                        "values": [
                            {"category": "Loss of Signal", "count": 120, "sla_status": "SLA Met"},
                            {"category": "Loss of Signal", "count": 8, "sla_status": "SLA Breached"},
                            {"category": "Slow Connection", "count": 85, "sla_status": "SLA Met"},
                            {"category": "Slow Connection", "count": 3, "sla_status": "SLA Breached"},
                        ]
                    },
                },
                "data": [
                    {"category": "Loss of Signal", "count": 120, "sla_status": "SLA Met"},
                    {"category": "Loss of Signal", "count": 8, "sla_status": "SLA Breached"},
                    {"category": "Slow Connection", "count": 85, "sla_status": "SLA Met"},
                    {"category": "Slow Connection", "count": 3, "sla_status": "SLA Breached"},
                ],
            }
        ],
        "audit_table": {
            "title": "Audit Tiket Gangguan NOC & Kepatuhan Service Level Agreement (SLA)",
            "description": "Rekam jejak insiden gangguan jaringan, waktu penanganan (MTTR), dan status SLA",
            "columns": [
                {"key": "ticket_id", "label": "No. Tiket", "type": "text"},
                {"key": "category", "label": "Kategori Insiden", "type": "text"},
                {"key": "service_area", "label": "Area Layanan", "type": "text"},
                {"key": "open_time", "label": "Waktu Lapor", "type": "date"},
                {"key": "mttr_hours", "label": "Durasi MTTR", "type": "text"},
                {"key": "sla_target", "label": "Target SLA", "type": "text"},
                {"key": "sla_status", "label": "Status SLA", "type": "badge"},
            ],
            "rows": [
                {"ticket_id": "TKT-2026-1042", "category": "Loss of Signal (Fiber Cut)", "service_area": "Jakarta Timur (Rawamangun)", "open_time": "2026-09-02 10:15", "mttr_hours": "1.8 Jam", "sla_target": "4.0 Jam", "sla_status": "SLA Met"},
            ],
            "total_records": 1,
        },
        "model_metadata": [
            {
                "model_name": "sla_breach_survival_v1",
                "version": "1.0.0",
                "prediction_window": "active_tickets",
                "confidence_score": 0.902,
                "last_trained_at": "2026-09-01T04:00:00Z",
            }
        ],
    },
    "overview": {
        "module": "overview",
        "as_of_date": "2026-09-01",
        "executive_summary": "Kinerja operasional ISP bulan September berada dalam zona sehat dengan pendapatan MRR Rp 1,45 M dan pemenuhan SLA 94.8%. Namun perhatian diperlukan pada risiko churn pelanggan segmen 50 Mbps dan penipisan stok kabel optik di Gudang Jakarta.",
        "key_metrics": [
            {
                "key": "mrr",
                "label": "Monthly Recurring Revenue",
                "value": 1450000000.0,
                "formatted_value": "Rp 1,45 M",
                "unit": "IDR",
                "change_percentage": 3.2,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "net_cashflow",
                "label": "Net Cash Flow",
                "value": 320000000.0,
                "formatted_value": "Rp 320 Jt",
                "unit": "IDR",
                "change_percentage": 5.4,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "sla_compliance",
                "label": "Pencapaian SLA Operasional",
                "value": 94.8,
                "formatted_value": "94.8%",
                "unit": "%",
                "change_percentage": 2.1,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "churn_risk",
                "label": "Pelanggan Risiko Churn",
                "value": 142.0,
                "formatted_value": "142 Akun",
                "unit": "customers",
                "change_percentage": 12.5,
                "trend": "up",
                "status": "critical",
            },
        ],
        "narrative_insights": [
            {
                "id": "ins-ovw-001",
                "domain": "overview",
                "severity": "warning",
                "title": "Sinergi Tindakan Komersial & Layanan Operasi",
                "narrative": "Pelanggan dengan risiko churn tertinggi terkonsentrasi pada wilayah yang sempat mengalami degradasi jaringan 2 pekan lalu. Rekomendasi tindakan kompensasi kuota untuk memulihkan kepuasan.",
                "suggested_actions": [
                    "Integrasikan laporan tiket gangguan ke tim customer success sebelum jadwal perpanjangan kontrak.",
                    "Lakukan restock kabel optik darurat untuk menghindari penundaan aktivasi pelanggan baru.",
                ],
            }
        ],
        "visualizations": [
            {
                "chart_id": "chart-domain-health",
                "title": "Indeks Kesehatan Domain Bisnis ISP",
                "description": "Skor performa 0-100 lintas 6 modul bisnis utama",
                "chart_library": "vega-lite",
                "spec": {
                    "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                    "mark": "bar",
                    "encoding": {
                        "x": {"field": "domain", "type": "nominal", "axis": {"title": "Modul Bisnis"}},
                        "y": {"field": "score", "type": "quantitative", "axis": {"title": "Indeks Performa (0-100)"}},
                        "color": {
                            "field": "status",
                            "type": "nominal",
                            "scale": {
                                "domain": ["Bagus", "Perhatian"],
                                "range": ["#22c55e", "#eab308"],
                            },
                        },
                    },
                    "data": {
                        "values": [
                            {"domain": "Commercial", "score": 82, "status": "Bagus"},
                            {"domain": "Finance", "score": 88, "status": "Bagus"},
                            {"domain": "Procurement", "score": 75, "status": "Perhatian"},
                            {"domain": "Inventory", "score": 68, "status": "Perhatian"},
                            {"domain": "Asset", "score": 85, "status": "Bagus"},
                            {"domain": "Service", "score": 92, "status": "Bagus"},
                        ]
                    },
                },
                "data": [
                    {"domain": "Commercial", "score": 82, "status": "Bagus"},
                    {"domain": "Finance", "score": 88, "status": "Bagus"},
                    {"domain": "Procurement", "score": 75, "status": "Perhatian"},
                    {"domain": "Inventory", "score": 68, "status": "Perhatian"},
                    {"domain": "Asset", "score": 85, "status": "Bagus"},
                    {"domain": "Service", "score": 92, "status": "Bagus"},
                ],
            }
        ],
        "audit_table": {
            "title": "Audit Indeks Kinerja & Kesehatan Antar Domain ISP",
            "description": "Evaluasi pencapaian metrik utama dan status operasional per unit bisnis",
            "columns": [
                {"key": "module", "label": "Modul Bisnis", "type": "text"},
                {"key": "primary_kpi", "label": "Metrik Utama", "type": "text"},
                {"key": "target", "label": "Target KPI", "type": "text"},
                {"key": "actual", "label": "Realisasi Aktual", "type": "text"},
                {"key": "health_score", "label": "Skor Kesehatan", "type": "number"},
                {"key": "status", "label": "Status", "type": "badge"},
            ],
            "rows": [
                {"module": "Commercial", "primary_kpi": "Monthly Recurring Revenue", "target": "Rp 1,40 M", "actual": "Rp 1,45 M", "health_score": 82, "status": "Bagus"},
                {"module": "Finance", "primary_kpi": "Net Operating Cash Flow", "target": "Rp 300 Jt", "actual": "Rp 320 Jt", "health_score": 88, "status": "Bagus"},
                {"module": "Procurement", "primary_kpi": "Vendor On-Time Delivery", "target": "90.0%", "actual": "83.3%", "health_score": 75, "status": "Perhatian"},
                {"module": "Inventory", "primary_kpi": "Stockout Runway Days", "target": "30 Hari", "actual": "11 Hari", "health_score": 68, "status": "Perhatian"},
                {"module": "Asset", "primary_kpi": "Rasio Perangkat Prima", "target": "95.0%", "actual": "96.2%", "health_score": 85, "status": "Bagus"},
                {"module": "Service", "primary_kpi": "Tingkat Kepatuhan SLA", "target": "92.0%", "actual": "94.8%", "health_score": 92, "status": "Bagus"},
            ],
            "total_records": 6,
        },
        "model_metadata": [
            {
                "model_name": "executive_state_compiler_v1",
                "version": "1.0.0",
                "prediction_window": "current_cycle",
                "confidence_score": 0.915,
                "last_trained_at": "2026-09-01T00:00:00Z",
            }
        ],
    },
}


@router.get(
    "/mock/{module}",
    response_model=ResponseEnvelope[InsightPackage],
    status_code=status.HTTP_200_OK,
    summary="Ambil Wawasan Bisnis per Modul (Mock Prototype)",
    description="Menyajikan paket wawasan eksekutif, KPI cards, penalaran agen, dan grafik Vega-Lite sesuai kontrak API.",
)
async def get_mock_insight(
    request: Request,
    module: str = Path(
        ...,
        description="Nama modul bisnis (overview, commercial, finance, procurement, inventory, asset, service)",
    ),
    as_of_date: Optional[str] = Query(
        default=None,
        description="Filter tanggal snapshot acuan (format YYYY-MM-DD)",
        pattern=r"^\d{4}-\d{2}-\d{2}$",
    ),
    current_user: dict = Depends(get_current_user),
):
    request_id = getattr(request.state, "request_id", None)
    normalized_module = module.lower().strip()

    if normalized_module not in MOCK_MODULE_INSIGHTS:
        valid_modules = ", ".join(sorted(MOCK_MODULE_INSIGHTS.keys()))
        raise EntityNotFoundError(
            message=f"Modul '{module}' tidak dikenali. Modul yang tersedia: {valid_modules}."
        )

    insight_raw = MOCK_MODULE_INSIGHTS[normalized_module].copy()
    if as_of_date:
        insight_raw["as_of_date"] = as_of_date

    insight_raw["generated_at"] = datetime.now(timezone.utc).isoformat()
    package = InsightPackage(**insight_raw)

    return success_response(data=package.model_dump(), request_id=request_id)
