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
