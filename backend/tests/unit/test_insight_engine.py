import pytest
from app.insights.chart_generator import (
    build_billing_delay_trend_chart,
    build_churn_distribution_chart,
)
from app.insights.llm_client import UnifiedLLMClient
from app.insights.validator import sanitize_and_parse_json, validate_insight_package
from app.schemas.insights import InsightPackage


@pytest.mark.asyncio
async def test_llm_client_critical_grounded_synthesis():
    """Verify that UnifiedLLMClient produces skeptical, fluff-free narratives directly from input data."""
    client = UnifiedLLMClient(provider="fallback")  # Test deterministic grounded generator

    metrics = {
        "mrr": 1450000000.0,
        "mrr_at_risk": 54000000.0,
        "high_churn_risk_count": 14,
        "active_subscribers": 120,
    }
    high_risk_custs = [
        {"customer_id": 101, "churn_probability": 0.85, "risk_level": "HIGH"}
    ]
    anomalies = [
        {"type": "CHRONIC_PAYMENT_DEFAULT", "severity": "CRITICAL", "description": "14 akun terlambat berulang"}
    ]

    result = await client.generate_insight_narrative(
        domain="commercial",
        as_of_date="2026-09-05",
        metrics=metrics,
        high_risk_customers=high_risk_custs,
        temporal_history=[],
        anomalies=anomalies,
    )

    assert "executive_summary" in result
    assert "narrative_insights" in result
    assert len(result["narrative_insights"]) > 0

    # Ensure tone is not cheerleading/fluff
    summary = result["executive_summary"].lower()
    assert "kinerja luar biasa" not in summary
    assert "pencapaian membanggakan" not in summary
    assert "ancaman" in summary or "risiko" in summary


def test_chart_generator_specs():
    """Verify that Vega-Lite v5 specs are structured accurately."""
    bar_chart = build_churn_distribution_chart(low_count=80, med_count=26, high_count=14)
    assert bar_chart["chart_library"] == "vega-lite"
    assert bar_chart["spec"]["$schema"] == "https://vega.github.io/schema/vega-lite/v5.json"
    assert len(bar_chart["data"]) == 3

    trend_chart = build_billing_delay_trend_chart(
        temporal_history=[{"period": "2026-08-01", "avg_days_late": 4.5, "total_invoices": 120}]
    )
    assert trend_chart["chart_library"] == "vega-lite"
    assert trend_chart["spec"]["mark"]["type"] == "line"


def test_validator_and_json_sanitizer():
    """Verify markdown code fence stripping and Pydantic validation."""
    raw_markdown_json = """
    ```json
    {
      "module": "commercial",
      "as_of_date": "2026-09-05",
      "executive_summary": "Tingkat churn berisiko tinggi terdeteksi pada 14 pelanggan.",
      "key_metrics": [],
      "narrative_insights": [],
      "visualizations": [],
      "model_metadata": [],
      "generated_at": "2026-09-05T06:00:00Z"
    }
    ```
    """

    parsed = sanitize_and_parse_json(raw_markdown_json)
    assert parsed["module"] == "commercial"

    validated = validate_insight_package(parsed)
    assert isinstance(validated, InsightPackage)
    assert validated.module == "commercial"
