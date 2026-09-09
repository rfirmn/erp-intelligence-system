import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.schemas.insights import InsightPackage


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_dashboard_overview_phase4_bi_and_audit(client: AsyncClient):
    """Verify that the Executive Overview endpoint serves aggregate macro KPIs, Vega-Lite chart, and audit table."""
    resp = await client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["success"] is True
    assert payload["data"] is not None

    package = InsightPackage(**payload["data"])
    assert package.module == "overview"

    # 1. Verify Macro KPI cards
    metric_keys = [m.key for m in package.key_metrics]
    assert "mrr" in metric_keys
    assert "active_customers" in metric_keys
    assert "collection_rate" in metric_keys

    # 2. Verify Visualizations
    chart_ids = [v.chart_id for v in package.visualizations]
    assert "chart-revenue-vs-payment" in chart_ids
    assert "chart-customer-growth" in chart_ids

    # 3. Verify Tabular Audit Data
    assert package.audit_table is not None
    assert package.audit_table.total_records > 0
    assert len(package.audit_table.rows) > 0
    col_keys = [c.key for c in package.audit_table.columns]
    assert "customer_id" in col_keys or "module" in col_keys


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "module,expected_kpi,expected_chart,expected_col",
    [
        ("commercial", "mrr", "chart-churn-distribution", "customer_id"),
        ("finance", "net_cashflow", "chart-ar-aging", "invoice_id"),
        ("procurement", "avg_lead_time", "chart-vendor-performance", "po_number"),
        ("inventory", "stockout_risk_items", "chart-stock-depletion", "sku"),
        ("asset", "assets_needing_maintenance", "chart-asset-health", "asset_id"),
        ("service", "sla_compliance", "chart-ticket-sla", "ticket_id"),
    ],
)
async def test_domain_modules_phase4_bi_and_audit(
    client: AsyncClient,
    module: str,
    expected_kpi: str,
    expected_chart: str,
    expected_col: str,
):
    """Verify that every domain module serves specialized KPI cards, charts, and granular audit records."""
    resp = await client.get(f"/api/v1/insights/{module}")
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["success"] is True

    package = InsightPackage(**payload["data"])
    assert package.module == module

    # Check KPI cards
    metric_keys = [m.key for m in package.key_metrics]
    assert expected_kpi in metric_keys

    # Check Vega-Lite charts
    chart_ids = [v.chart_id for v in package.visualizations]
    assert expected_chart in chart_ids

    # Check Tabular Audit dataset
    assert package.audit_table is not None
    assert package.audit_table.total_records > 0
    assert len(package.audit_table.rows) > 0
    col_keys = [c.key for c in package.audit_table.columns]
    assert expected_col in col_keys


@pytest.mark.asyncio
async def test_invalid_module_404_handling(client: AsyncClient):
    """Verify that an invalid module identifier returns standard HTTP 404 envelope."""
    resp = await client.get("/api/v1/insights/invalid_unknown_domain")
    assert resp.status_code == 404

    payload = resp.json()
    assert payload["success"] is False
    assert payload["data"] is None
    assert payload["error"]["code"] == "NOT_FOUND" or "tidak valid" in payload["error"]["message"]
