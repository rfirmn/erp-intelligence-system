from typing import Any, Dict, List, Optional


def build_churn_distribution_chart(
    low_count: int,
    med_count: int,
    high_count: int,
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 specification for Customer Churn Risk distribution."""
    chart_data = [
        {"risk_tier": "Rendah", "count": low_count},
        {"risk_tier": "Sedang", "count": med_count},
        {"risk_tier": "Tinggi", "count": high_count},
    ]

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Distribusi Probabilitas Churn Pelanggan ISP",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {
                "field": "risk_tier",
                "type": "nominal",
                "axis": {"title": "Tingkat Risiko", "labelAngle": 0},
            },
            "y": {
                "field": "count",
                "type": "quantitative",
                "axis": {"title": "Jumlah Pelanggan"},
            },
            "color": {
                "field": "risk_tier",
                "type": "nominal",
                "scale": {
                    "domain": ["Rendah", "Sedang", "Tinggi"],
                    "range": ["#22c55e", "#eab308", "#ef4444"],
                },
                "legend": {"title": "Kategori Risiko"},
            },
        },
        "data": {"values": chart_data},
    }

    return {
        "chart_id": "chart-churn-distribution",
        "title": "Distribusi Tingkat Risiko Churn Pelanggan",
        "description": "Pengelompokan pelanggan berdasarkan probabilitas churn model XGBoost",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": chart_data,
    }


def build_billing_delay_trend_chart(
    temporal_history: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 specification for temporal billing delay velocity."""
    chart_data = temporal_history or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Tren Rata-Rata Keterlambatan Pembayaran Bulanan",
        "mark": {"type": "line", "point": True, "strokeWidth": 3},
        "encoding": {
            "x": {
                "field": "period",
                "type": "nominal",
                "axis": {"title": "Periode Tagihan", "labelAngle": -20},
            },
            "y": {
                "field": "avg_days_late",
                "type": "quantitative",
                "axis": {"title": "Rata-Rata Keterlambatan (Hari)"},
            },
            "color": {"value": "#f97316"},
            "tooltip": [
                {"field": "period", "type": "nominal", "title": "Bulan"},
                {"field": "avg_days_late", "type": "quantitative", "title": "Hari Telat"},
                {"field": "total_invoices", "type": "quantitative", "title": "Total Faktur"},
            ],
        },
        "data": {"values": chart_data},
    }

    return {
        "chart_id": "chart-billing-delay-trend",
        "title": "Akselerasi Keterlambatan Pembayaran (Multi-Snapshot)",
        "description": "Pergerakan rata-rata hari keterlambatan penagihan dari periode ke periode",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": chart_data,
    }


def build_domain_health_chart(
    domain_scores: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 specification for cross-module ISP Performance Health Index."""
    chart_data = domain_scores or [
        {"domain": "Commercial", "score": 82, "status": "Bagus"},
        {"domain": "Finance", "score": 88, "status": "Bagus"},
        {"domain": "Procurement", "score": 75, "status": "Perhatian"},
        {"domain": "Inventory", "score": 68, "status": "Perhatian"},
        {"domain": "Asset", "score": 85, "status": "Bagus"},
        {"domain": "Service", "score": 92, "status": "Bagus"},
    ]

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Indeks Kesehatan Domain Bisnis ISP",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {"field": "domain", "type": "nominal", "axis": {"title": "Modul Bisnis", "labelAngle": 0}},
            "y": {"field": "score", "type": "quantitative", "axis": {"title": "Indeks Performa (0-100)"}, "scale": {"domain": [0, 100]}},
            "color": {
                "field": "status",
                "type": "nominal",
                "scale": {
                    "domain": ["Bagus", "Perhatian"],
                    "range": ["#22c55e", "#eab308"],
                },
                "legend": {"title": "Status Operasional"},
            },
        },
        "data": {"values": chart_data},
    }

    return {
        "chart_id": "chart-domain-health",
        "title": "Indeks Kesehatan Domain Bisnis ISP",
        "description": "Skor performa 0-100 lintas 6 modul bisnis utama",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": chart_data,
    }


def build_ar_aging_chart(
    buckets: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 specification for Finance Accounts Receivable (AR) Aging breakdown."""
    chart_data = buckets or [
        {"bucket": "0-30 Hari", "amount": 160000000, "formatted_amount": "Rp 160 Jt"},
        {"bucket": "31-60 Hari", "amount": 55000000, "formatted_amount": "Rp 55 Jt"},
        {"bucket": ">60 Hari", "amount": 30000000, "formatted_amount": "Rp 30 Jt"},
    ]

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Komposisi Umur Piutang (AR Aging)",
        "mark": {"type": "arc", "innerRadius": 50},
        "encoding": {
            "theta": {"field": "amount", "type": "quantitative"},
            "color": {
                "field": "bucket",
                "type": "nominal",
                "scale": {
                    "domain": ["0-30 Hari", "31-60 Hari", ">60 Hari"],
                    "range": ["#22c55e", "#eab308", "#ef4444"],
                },
                "legend": {"title": "Rentang Umur Tagihan"},
            },
            "tooltip": [
                {"field": "bucket", "type": "nominal", "title": "Bucket"},
                {"field": "formatted_amount", "type": "nominal", "title": "Nominal Piutang"},
            ],
        },
        "data": {"values": chart_data},
    }

    return {
        "chart_id": "chart-ar-aging",
        "title": "Komposisi AR Aging (Umur Piutang)",
        "description": "Distribusi nominal piutang berdasarkan rentang keterlambatan jatuh tempo",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": chart_data,
    }


def build_vendor_performance_chart(
    vendors: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 specification for Procurement Vendor On-Time Delivery score."""
    chart_data = vendors or [
        {"vendor": "PT Optik Nusantara", "score": 94, "target": 90},
        {"vendor": "PT Telko Supply", "score": 68, "target": 90},
        {"vendor": "PT Router Mandiri", "score": 88, "target": 90},
    ]

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Skor Pemenuhan Waktu Vendor Utama (OTD)",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {"field": "vendor", "type": "nominal", "axis": {"title": "Vendor", "labelAngle": 0}},
            "y": {"field": "score", "type": "quantitative", "axis": {"title": "Skor OTD (%)"}, "scale": {"domain": [0, 100]}},
            "color": {
                "condition": {"test": "datum.score >= 85", "value": "#22c55e"},
                "value": "#ef4444",
            },
            "tooltip": [
                {"field": "vendor", "type": "nominal", "title": "Vendor"},
                {"field": "score", "type": "quantitative", "title": "Skor OTD (%)"},
            ],
        },
        "data": {"values": chart_data},
    }

    return {
        "chart_id": "chart-vendor-performance",
        "title": "Skor Pemenuhan Waktu Vendor Utama",
        "description": "Persentase On-Time Delivery per vendor kuartal ini vs target 90%",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": chart_data,
    }


def build_stock_depletion_chart(
    projections: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 specification for Inventory Stock Depletion vs Safety Stock."""
    chart_data = projections or [
        {"day": "Hari 1", "remaining_stock": 4200, "safety_stock": 1500},
        {"day": "Hari 5", "remaining_stock": 2800, "safety_stock": 1500},
        {"day": "Hari 10", "remaining_stock": 800, "safety_stock": 1500},
        {"day": "Hari 15", "remaining_stock": 0, "safety_stock": 1500},
    ]

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Proyeksi Penurunan Stok Material Kritis vs Batas Kritis",
        "mark": {"type": "line", "point": True, "strokeWidth": 3},
        "encoding": {
            "x": {"field": "day", "type": "ordinal", "axis": {"title": "Proyeksi Hari ke Depan"}},
            "y": {"field": "remaining_stock", "type": "quantitative", "axis": {"title": "Sisa Stok (Meter/Unit)"}},
            "color": {"value": "#ef4444"},
            "tooltip": [
                {"field": "day", "type": "ordinal", "title": "Timeline"},
                {"field": "remaining_stock", "type": "quantitative", "title": "Sisa Stok"},
                {"field": "safety_stock", "type": "quantitative", "title": "Batas Safety"},
            ],
        },
        "data": {"values": chart_data},
    }

    return {
        "chart_id": "chart-stock-depletion",
        "title": "Proyeksi Penurunan Stok Material Kritis",
        "description": "Laju konsumsi material drop cable vs batas minimum safety stock",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": chart_data,
    }


def build_asset_health_chart(
    status_breakdown: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 specification for Network Hardware Operational Health."""
    chart_data = status_breakdown or [
        {"status": "Prima", "count": 240},
        {"status": "Perlu Pemeliharaan", "count": 14},
        {"status": "Kritis", "count": 2},
    ]

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Distribusi Kondisi Aset Jaringan",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {"field": "status", "type": "nominal", "axis": {"title": "Status Operasional", "labelAngle": 0}},
            "y": {"field": "count", "type": "quantitative", "axis": {"title": "Jumlah Perangkat"}},
            "color": {
                "field": "status",
                "type": "nominal",
                "scale": {
                    "domain": ["Prima", "Perlu Pemeliharaan", "Kritis"],
                    "range": ["#22c55e", "#eab308", "#ef4444"],
                },
            },
        },
        "data": {"values": chart_data},
    }

    return {
        "chart_id": "chart-asset-health",
        "title": "Distribusi Kondisi Aset Jaringan",
        "description": "Kondisi operasional router, OLT, dan switch POP distribusi",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": chart_data,
    }


def build_ticket_sla_chart(
    ticket_sla_data: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 specification for NOC Ticket SLA Resolution compliance."""
    chart_data = ticket_sla_data or [
        {"category": "Loss of Signal", "count": 120, "sla_status": "SLA Met"},
        {"category": "Loss of Signal", "count": 8, "sla_status": "SLA Breached"},
        {"category": "Slow Connection", "count": 85, "sla_status": "SLA Met"},
        {"category": "Slow Connection", "count": 3, "sla_status": "SLA Breached"},
    ]

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Proporsi Tiket Selesai vs SLA Breach per Kategori",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {"field": "category", "type": "nominal", "axis": {"title": "Kategori Insiden", "labelAngle": 0}},
            "y": {"field": "count", "type": "quantitative", "axis": {"title": "Jumlah Tiket"}},
            "xOffset": {"field": "sla_status"},
            "color": {
                "field": "sla_status",
                "type": "nominal",
                "scale": {
                    "domain": ["SLA Met", "SLA Breached"],
                    "range": ["#22c55e", "#ef4444"],
                },
                "legend": {"title": "Status SLA"},
            },
        },
        "data": {"values": chart_data},
    }

    return {
        "chart_id": "chart-ticket-sla",
        "title": "Tren Penyelesaian Tiket per Kategori",
        "description": "Proporsi tiket diselesaikan dalam batas SLA vs SLA Breach",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": chart_data,
    }


# =============================================================================
# PHASE 1 DIRECT DATASTORE CHARTS (OVERVIEW, COMMERCIAL, FINANCE)
# =============================================================================

def build_revenue_vs_payment_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 dual-line / grouped bar chart for Invoiced vs Collected Revenue."""
    data = chart_data or []
    # Reshape into long form for easy Vega-Lite grouped encoding
    long_data = []
    for row in data:
        long_data.append({
            "month": row.get("month", "N/A"),
            "tipe": "Tagihan (Invoiced)",
            "amount": row.get("invoiced", 0.0),
        })
        long_data.append({
            "month": row.get("month", "N/A"),
            "tipe": "Realisasi Kas (Collected)",
            "amount": row.get("collected", 0.0),
        })

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Perbandingan Tagihan vs Pembayaran Masuk per Bulan",
        "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {
            "x": {
                "field": "month",
                "type": "nominal",
                "axis": {"title": "Bulan", "labelAngle": -25},
            },
            "y": {
                "field": "amount",
                "type": "quantitative",
                "axis": {"title": "Jumlah (IDR)", "format": "s"},
            },
            "xOffset": {"field": "tipe"},
            "color": {
                "field": "tipe",
                "type": "nominal",
                "scale": {
                    "domain": ["Tagihan (Invoiced)", "Realisasi Kas (Collected)"],
                    "range": ["#3b82f6", "#10b981"],
                },
                "legend": {"title": "Arus Kas"},
            },
            "tooltip": [
                {"field": "month", "type": "nominal", "title": "Bulan"},
                {"field": "tipe", "type": "nominal", "title": "Kategori"},
                {"field": "amount", "type": "quantitative", "title": "Total (Rp)", "format": ",.0f"},
            ],
        },
        "data": {"values": long_data},
    }

    return {
        "chart_id": "chart-revenue-vs-payment",
        "title": "Tren Revenue vs Realisasi Pembayaran",
        "description": "Perbandingan tagihan faktur yang diterbitkan vs realisasi pembayaran masuk bulanan",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_customer_growth_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 area/line chart for customer acquisition growth."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Tren Pertumbuhan Akumulasi Pelanggan ISP",
        "mark": {"type": "area", "line": {"color": "#6366f1", "width": 2}, "color": {
            "x1": 1, "y1": 1, "x2": 1, "y2": 0,
            "gradient": "linear",
            "stops": [
                {"offset": 0, "color": "white"},
                {"offset": 1, "color": "#6366f1"}
            ]
        }},
        "encoding": {
            "x": {
                "field": "month",
                "type": "nominal",
                "axis": {"title": "Periode Bulan", "labelAngle": -25},
            },
            "y": {
                "field": "cumulative_customers" if data and "cumulative_customers" in data[0] else "new_customers",
                "type": "quantitative",
                "axis": {"title": "Total Pelanggan"},
            },
            "tooltip": [
                {"field": "month", "type": "nominal", "title": "Bulan"},
                {"field": "new_customers", "type": "quantitative", "title": "Pelanggan Baru"},
                {"field": "cumulative_customers", "type": "quantitative", "title": "Akumulasi"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-customer-growth",
        "title": "Tren Pertumbuhan Pelanggan Baru & Basis Pelanggan",
        "description": "Kinerja akuisisi dan pertumbuhan jumlah pelanggan aktif dari waktu ke waktu",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_package_mix_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 horizontal bar chart for internet package composition."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Komposisi Distribusi Paket Langganan Aktif",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "y": {
                "field": "package_name",
                "type": "nominal",
                "axis": {"title": "Nama Paket", "labelAngle": 0},
                "sort": "-x",
            },
            "x": {
                "field": "subscriptions",
                "type": "quantitative",
                "axis": {"title": "Jumlah Langganan"},
            },
            "color": {
                "field": "package_name",
                "type": "nominal",
                "scale": {"scheme": "tableau10"},
                "legend": None,
            },
            "tooltip": [
                {"field": "package_name", "type": "nominal", "title": "Paket"},
                {"field": "subscriptions", "type": "quantitative", "title": "Jumlah Langganan"},
                {"field": "total_mrr", "type": "quantitative", "title": "Total MRR", "format": ",.0f"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-package-mix",
        "title": "Komposisi Portofolio Paket Langganan",
        "description": "Distribusi paket internet broadband yang paling banyak digunakan pelanggan aktif",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_mrr_per_package_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for MRR contribution per package."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Kontribusi Monthly Recurring Revenue per Paket",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {
                "field": "package_name",
                "type": "nominal",
                "axis": {"title": "Paket Internet", "labelAngle": -20},
            },
            "y": {
                "field": "total_mrr",
                "type": "quantitative",
                "axis": {"title": "Total MRR (IDR)", "format": "s"},
            },
            "color": {"value": "#0284c7"},
            "tooltip": [
                {"field": "package_name", "type": "nominal", "title": "Paket"},
                {"field": "total_mrr", "type": "quantitative", "title": "MRR (Rp)", "format": ",.0f"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-mrr-per-package",
        "title": "Kontribusi Revenue (MRR) per Jenis Paket",
        "description": "Porsi pendapatan berulang bulanan yang dihasilkan dari masing-masing paket layanan",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_customers_per_city_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for geographic distribution of customers."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Sebaran Geografis Pelanggan Berdasarkan Kota / Wilayah",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "y": {
                "field": "city",
                "type": "nominal",
                "axis": {"title": "Kota / Wilayah Operasional"},
                "sort": "-x",
            },
            "x": {
                "field": "count",
                "type": "quantitative",
                "axis": {"title": "Jumlah Pelanggan"},
            },
            "color": {"value": "#8b5cf6"},
            "tooltip": [
                {"field": "city", "type": "nominal", "title": "Kota"},
                {"field": "count", "type": "quantitative", "title": "Pelanggan"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-customers-per-city",
        "title": "Sebaran Pelanggan per Kota / Wilayah",
        "description": "Kepadatan basis pelanggan aktif untuk perencanaan kapasitas coverage dan teknisi",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_ar_aging_buckets_chart(
    chart_data: List[Dict[str, Any]],
    chart_id: str = "chart-ar-aging",
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for Accounts Receivable aging buckets."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Analisis Umur Piutang (AR Aging Breakdown)",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {
                "field": "bucket",
                "type": "nominal",
                "axis": {"title": "Kategori Umur Jatuh Tempo", "labelAngle": 0},
            },
            "y": {
                "field": "amount",
                "type": "quantitative",
                "axis": {"title": "Total Piutang (IDR)", "format": "s"},
            },
            "color": {
                "field": "bucket",
                "type": "nominal",
                "scale": {
                    "domain": ["0–30 Hari", "31–60 Hari", "61–90 Hari", "60+ Hari", "90+ Hari"],
                    "range": ["#22c55e", "#eab308", "#f97316", "#ef4444", "#dc2626"],
                },
                "legend": {"title": "Tingkat Keterlambatan"},
            },
            "tooltip": [
                {"field": "bucket", "type": "nominal", "title": "Umur Piutang"},
                {"field": "amount", "type": "quantitative", "title": "Total Tagihan (Rp)", "format": ",.0f"},
                {"field": "count", "type": "quantitative", "title": "Jumlah Faktur"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": chart_id,
        "title": "Distribusi Umur Piutang (AR Aging)",
        "description": "Pengelompokan piutang berdasarkan lama hari keterlambatan dari tanggal jatuh tempo",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_installations_per_month_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for monthly installation completions."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Volume Penyelesaian Instalasi Pelanggan per Bulan",
        "mark": {"type": "line", "point": True, "strokeWidth": 2},
        "encoding": {
            "x": {
                "field": "month",
                "type": "nominal",
                "axis": {"title": "Bulan", "labelAngle": -20},
            },
            "y": {
                "field": "count",
                "type": "quantitative",
                "axis": {"title": "Instalasi Selesai"},
            },
            "color": {"value": "#06b6d4"},
            "tooltip": [
                {"field": "month", "type": "nominal", "title": "Bulan"},
                {"field": "count", "type": "quantitative", "title": "Instalasi"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-installations-per-month",
        "title": "Aktivitas Instalasi Baru per Bulan",
        "description": "Kecepatan dan volume instalasi jaringan pelanggan baru oleh tim teknisi lapangan",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_billing_day_concentration_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for billing cycle day distribution."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Konsentrasi Tanggal Siklus Tagihan (Billing Day)",
        "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {
            "x": {
                "field": "billing_day",
                "type": "nominal",
                "axis": {"title": "Tanggal Tagihan", "labelAngle": -45},
            },
            "y": {
                "field": "count",
                "type": "quantitative",
                "axis": {"title": "Jumlah Langganan"},
            },
            "color": {"value": "#14b8a6"},
            "tooltip": [
                {"field": "billing_day", "type": "nominal", "title": "Siklus"},
                {"field": "count", "type": "quantitative", "title": "Jumlah Langganan"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-billing-day-concentration",
        "title": "Konsentrasi Tanggal Billing Pelanggan",
        "description": "Distribusi tanggal penagihan langganan untuk menghindari beban penagihan menumpuk",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_tenure_distribution_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for customer tenure distribution."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Distribusi Lama Berlangganan (Tenure)",
        "mark": {"type": "bar", "cornerRadiusEnd": 4},
        "encoding": {
            "x": {
                "field": "tenure_bucket",
                "type": "nominal",
                "axis": {"title": "Rentang Durasi Berlangganan", "labelAngle": 0},
            },
            "y": {
                "field": "count",
                "type": "quantitative",
                "axis": {"title": "Jumlah Langganan"},
            },
            "color": {
                "field": "tenure_bucket",
                "type": "nominal",
                "scale": {"scheme": "purples"},
                "legend": None,
            },
            "tooltip": [
                {"field": "tenure_bucket", "type": "nominal", "title": "Kategori Tenure"},
                {"field": "count", "type": "quantitative", "title": "Jumlah Pelanggan"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-tenure-distribution",
        "title": "Distribusi Lama Berlangganan Pelanggan (Tenure)",
        "description": "Profil loyalitas dan kematangan masa berlangganan basis pelanggan ISP",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_overdue_trend_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for monthly overdue receivable amount trend."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Tren Nilai Piutang Tertunggak per Bulan Jatuh Tempo",
        "mark": {"type": "line", "point": True, "strokeWidth": 2.5},
        "encoding": {
            "x": {
                "field": "due_month",
                "type": "nominal",
                "axis": {"title": "Bulan Jatuh Tempo", "labelAngle": -20},
            },
            "y": {
                "field": "overdue_amount",
                "type": "quantitative",
                "axis": {"title": "Total Overdue (IDR)", "format": "s"},
            },
            "color": {"value": "#ef4444"},
            "tooltip": [
                {"field": "due_month", "type": "nominal", "title": "Bulan"},
                {"field": "overdue_amount", "type": "quantitative", "title": "Overdue (Rp)", "format": ",.0f"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-overdue-trend",
        "title": "Tren Akumulasi Piutang Jatuh Tempo (Overdue)",
        "description": "Pergerakan jumlah nilai piutang yang lewat jatuh tempo dari bulan ke bulan",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_tax_trend_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for monthly tax (PPN) generation."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Tren Pajak PPN 11% yang Terhimpun Bulanan",
        "mark": {"type": "bar", "cornerRadiusEnd": 3},
        "encoding": {
            "x": {
                "field": "month",
                "type": "nominal",
                "axis": {"title": "Bulan Tagihan", "labelAngle": -20},
            },
            "y": {
                "field": "tax_amount",
                "type": "quantitative",
                "axis": {"title": "Pajak Terhimpun (IDR)", "format": "s"},
            },
            "color": {"value": "#f59e0b"},
            "tooltip": [
                {"field": "month", "type": "nominal", "title": "Bulan"},
                {"field": "tax_amount", "type": "quantitative", "title": "PPN (Rp)", "format": ",.0f"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-tax-trend",
        "title": "Tren Estimasi Pajak Terhimpun (PPN 11%)",
        "description": "Porsi pajak pertambahan nilai dari faktur penjualan bulanan",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }


def build_payment_method_mix_chart(
    chart_data: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """Construct Vega-Lite v5 chart for payment method distribution."""
    data = chart_data or []

    spec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "description": "Distribusi Transaksi per Metode Pembayaran",
        "mark": {"type": "arc", "innerRadius": 50},
        "encoding": {
            "theta": {"field": "total_amount", "type": "quantitative"},
            "color": {
                "field": "method",
                "type": "nominal",
                "scale": {"scheme": "category10"},
                "legend": {"title": "Metode Pembayaran"},
            },
            "tooltip": [
                {"field": "method", "type": "nominal", "title": "Metode"},
                {"field": "transactions", "type": "quantitative", "title": "Transaksi"},
                {"field": "total_amount", "type": "quantitative", "title": "Total Nominal (Rp)", "format": ",.0f"},
            ],
        },
        "data": {"values": data},
    }

    return {
        "chart_id": "chart-payment-method-mix",
        "title": "Proporsi Saluran Metode Pembayaran",
        "description": "Sebaran preferensi pembayaran tagihan oleh pelanggan",
        "chart_library": "vega-lite",
        "spec": spec,
        "data": data,
    }

