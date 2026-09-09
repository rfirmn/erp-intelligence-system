"""Integration tests for Phase 1 Direct SQL Datastore Analytics API.
Tests live execution against PostgreSQL datastore for Overview, Commercial, and Finance domains.
"""

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
async def test_overview_direct_datastore_analytics(client: AsyncClient):
    """Verify that Overview endpoint computes live metrics, 3 charts, and audit table."""
    resp = await client.get("/api/v1/dashboard/overview")
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["success"] is True
    assert payload["data"] is not None

    package = InsightPackage(**payload["data"])
    assert package.module == "overview"

    # Verify KPI Cards
    metric_map = {m.key: m for m in package.key_metrics}
    assert "active_customers" in metric_map
    assert "mrr" in metric_map
    assert "unpaid_ar" in metric_map
    assert "collection_rate" in metric_map

    # Real data assertions from datastore
    assert metric_map["active_customers"].value > 0
    assert metric_map["mrr"].value > 0
    assert metric_map["collection_rate"].value > 0

    # Verify Visualizations
    chart_ids = [v.chart_id for v in package.visualizations]
    assert "chart-revenue-vs-payment" in chart_ids
    assert "chart-customer-growth" in chart_ids
    assert "chart-package-mix" in chart_ids

    # Verify Audit Table default (Top Revenue at Risk)
    assert package.audit_table is not None
    assert package.audit_table.total_records > 0
    assert "customer_id" in [c.key for c in package.audit_table.columns]


@pytest.mark.asyncio
async def test_overview_data_quality_table_query(client: AsyncClient):
    """Verify that Overview endpoint supports ?table=data_quality selector."""
    resp = await client.get("/api/v1/dashboard/overview?table=data_quality")
    assert resp.status_code == 200

    package = InsightPackage(**resp.json()["data"])
    assert package.audit_table is not None
    assert "Data Quality" in package.audit_table.title
    assert package.audit_table.total_records > 0
    assert "check_name" in [c.key for c in package.audit_table.columns]


@pytest.mark.asyncio
async def test_commercial_direct_datastore_analytics(client: AsyncClient):
    """Verify that Commercial endpoint computes live KPIs, 8 charts, and audit table."""
    resp = await client.get("/api/v1/insights/commercial")
    assert resp.status_code == 200

    payload = resp.json()
    assert payload["success"] is True

    package = InsightPackage(**payload["data"])
    assert package.module == "commercial"

    # Verify 6 KPI Cards
    metric_map = {m.key: m for m in package.key_metrics}
    assert "active_customers" in metric_map
    assert "active_subscriptions" in metric_map
    assert "mrr" in metric_map
    assert "unpaid_customers" in metric_map
    assert "avg_tenure" in metric_map
    assert "churn_proxy" in metric_map

    assert metric_map["active_customers"].value > 0
    assert metric_map["active_subscriptions"].value > 0

    # Verify Visualizations (at least 8 charts)
    chart_ids = [v.chart_id for v in package.visualizations]
    assert len(chart_ids) >= 8
    assert "chart-customer-growth" in chart_ids
    assert "chart-package-mix" in chart_ids
    assert "chart-mrr-per-package" in chart_ids
    assert "chart-customers-per-city" in chart_ids
    assert "chart-ar-aging-commercial" in chart_ids
    assert "chart-installations-per-month" in chart_ids
    assert "chart-billing-day-concentration" in chart_ids
    assert "chart-tenure-distribution" in chart_ids

    # Verify Default Audit Table (Top Unpaid)
    assert package.audit_table is not None
    assert "Top Unpaid Customers" in package.audit_table.title
    assert package.audit_table.total_records > 0


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "table_param,expected_title_part",
    [
        ("revenue_at_risk", "Revenue at Risk"),
        ("customers_without_sub", "Without Active Subscription"),
        ("top_revenue", "Top Revenue Customers"),
    ],
)
async def test_commercial_table_parameter_switching(client: AsyncClient, table_param: str, expected_title_part: str):
    """Verify that Commercial endpoint accurately switches audit table via ?table=."""
    resp = await client.get(f"/api/v1/insights/commercial?table={table_param}")
    assert resp.status_code == 200

    package = InsightPackage(**resp.json()["data"])
    assert package.audit_table is not None
    assert expected_title_part.lower() in package.audit_table.title.lower()


@pytest.mark.asyncio
async def test_finance_direct_datastore_analytics(client: AsyncClient):
    """Verify that Finance endpoint computes 7 live KPIs, 5 charts, and overdue table."""
    resp = await client.get("/api/v1/insights/finance")
    assert resp.status_code == 200

    package = InsightPackage(**resp.json()["data"])
    assert package.module == "finance"

    # Verify 7 KPI Cards
    metric_map = {m.key: m for m in package.key_metrics}
    assert "total_invoiced" in metric_map
    assert "total_paid" in metric_map
    assert "outstanding_ar" in metric_map
    assert "collection_rate" in metric_map
    assert "dso" in metric_map
    assert "tax_collected" in metric_map
    assert "partial_payment_rate" in metric_map

    assert metric_map["total_invoiced"].value > 0
    assert metric_map["total_paid"].value > 0

    # Verify 5 Visualizations
    chart_ids = [v.chart_id for v in package.visualizations]
    assert "chart-revenue-vs-payment" in chart_ids
    assert "chart-ar-aging" in chart_ids
    assert "chart-payment-method-mix" in chart_ids
    assert "chart-overdue-trend" in chart_ids
    assert "chart-tax-trend" in chart_ids

    # Verify Default Audit Table
    assert package.audit_table is not None
    assert "Overdue Invoices" in package.audit_table.title


@pytest.mark.asyncio
async def test_finance_discrepancies_table_query(client: AsyncClient):
    """Verify that Finance endpoint returns payment completeness exceptions."""
    resp = await client.get("/api/v1/insights/finance?table=discrepancies")
    assert resp.status_code == 200

    package = InsightPackage(**resp.json()["data"])
    assert package.audit_table is not None
    assert "Payment Completeness" in package.audit_table.title
    assert "balance_due" in [c.key for c in package.audit_table.columns]
