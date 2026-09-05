from typing import Any, Dict, List


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
