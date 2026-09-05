from typing import Any, Dict, List, Optional


def explain_customer_risk(features: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Derive interpretable risk drivers for an individual customer.
    
    Translates quantitative features and model contributions into explainable statements
    ready to be consumed by the LangGraph agent and frontend cards.
    """
    drivers: List[Dict[str, Any]] = []

    late_3m = features.get("late_payment_count_3m") or 0
    late_6m = features.get("late_payment_count_6m") or 0
    avg_delay = features.get("avg_payment_delay_days_3m") or 0.0
    trend = features.get("payment_status_trend") or "STABLE"
    tenure = features.get("tenure_months") or 0.0
    fee = features.get("monthly_fee_current") or 0.0

    # 1. Late Payment Frequency
    if late_3m >= 2:
        drivers.append({
            "feature": "late_payment_count_3m",
            "impact": "INCREASES_RISK",
            "severity": "HIGH",
            "importance_weight": 0.35,
            "value": late_3m,
            "description": f"{late_3m} kali tagihan terlambat dalam 3 bulan terakhir",
        })
    elif late_3m == 1:
        drivers.append({
            "feature": "late_payment_count_3m",
            "impact": "INCREASES_RISK",
            "severity": "MEDIUM",
            "importance_weight": 0.18,
            "value": late_3m,
            "description": "1 kali keterlambatan pembayaran dalam kuartal terakhir",
        })

    # 2. Payment Trend Acceleration
    if trend == "WORSENING":
        drivers.append({
            "feature": "payment_status_trend",
            "impact": "INCREASES_RISK",
            "severity": "HIGH",
            "importance_weight": 0.28,
            "value": trend,
            "description": "Tren kedisiplinan pembayaran memburuk (WORSENING)",
        })
    elif trend == "IMPROVING":
        drivers.append({
            "feature": "payment_status_trend",
            "impact": "DECREASES_RISK",
            "severity": "LOW",
            "importance_weight": -0.15,
            "value": trend,
            "description": "Pola pembayaran menunjukkan perbaikan (IMPROVING)",
        })

    # 3. Average Delay Severity
    if avg_delay >= 15.0:
        drivers.append({
            "feature": "avg_payment_delay_days_3m",
            "impact": "INCREASES_RISK",
            "severity": "HIGH",
            "importance_weight": 0.22,
            "value": round(avg_delay, 1),
            "description": f"Rata-rata keterlambatan pembayaran mencapai {round(avg_delay, 1)} hari",
        })
    elif avg_delay >= 5.0:
        drivers.append({
            "feature": "avg_payment_delay_days_3m",
            "impact": "INCREASES_RISK",
            "severity": "MEDIUM",
            "importance_weight": 0.12,
            "value": round(avg_delay, 1),
            "description": f"Rata-rata terlambat bayar {round(avg_delay, 1)} hari dari jatuh tempo",
        })

    # 4. Tenure Loyalty Cushion or New Customer Vulnerability
    if tenure >= 24.0:
        drivers.append({
            "feature": "tenure_months",
            "impact": "DECREASES_RISK",
            "severity": "LOW",
            "importance_weight": -0.20,
            "value": round(tenure, 1),
            "description": f"Pelanggan loyal jangka panjang ({round(tenure / 12.0, 1)} tahun berlangganan)",
        })
    elif tenure < 6.0:
        drivers.append({
            "feature": "tenure_months",
            "impact": "INCREASES_RISK",
            "severity": "MEDIUM",
            "importance_weight": 0.15,
            "value": round(tenure, 1),
            "description": f"Pelanggan baru ({round(tenure, 1)} bulan) pada fase adaptasi rentan churn",
        })

    # 5. High Fee Exposure
    if fee >= 1000000.0:
        drivers.append({
            "feature": "monthly_fee_current",
            "impact": "EXPOSURE_WEIGHT",
            "severity": "HIGH",
            "importance_weight": 0.10,
            "value": fee,
            "description": f"Paket bernilai strategis tinggi (Rp {fee:,.0f}/bulan)",
        })

    # Sort by absolute weight descending and pick top 3
    drivers.sort(key=lambda d: abs(d.get("importance_weight", 0.0)), reverse=True)
    return drivers[:3]
