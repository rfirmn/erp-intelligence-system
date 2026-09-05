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
async def test_dashboard_overview_production_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/dashboard/overview")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    assert payload["error"] is None
    assert "request_id" in payload["meta"]

    # Validate against strict InsightPackage schema
    package = InsightPackage(**payload["data"])
    assert package.module == "overview"
    assert len(package.key_metrics) > 0
    assert len(package.visualizations) > 0


@pytest.mark.asyncio
async def test_commercial_insights_production_endpoint(client: AsyncClient):
    response = await client.get("/api/v1/insights/commercial")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True

    package = InsightPackage(**payload["data"])
    assert package.module == "commercial"
    assert len(package.key_metrics) >= 4

    # Verify presence of Vega-Lite visual specs
    chart_ids = [v.chart_id for v in package.visualizations]
    assert "chart-churn-distribution" in chart_ids

    # Verify critical tone
    summary = package.executive_summary.lower()
    assert "kinerja luar biasa" not in summary
