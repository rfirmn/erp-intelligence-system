from datetime import date, datetime, timezone
import pytest
from httpx import ASGITransport, AsyncClient
from sqlmodel import col, select

from app.core.session import async_session_factory
from app.ingestion.transformers.dim_customer_scd2 import sync_dim_customer_scd2
from app.main import app
from app.models.dimensions import DimCustomer


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_ingestion_source_mode(client: AsyncClient):
    """Verify source mode reveals MOCK_GENERATOR status with prominent warnings."""
    response = await client.get("/api/v1/ingestion/source-mode")
    assert response.status_code == 200

    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert "source_type" in data
    assert data["source_type"] == "MOCK_GENERATOR"
    assert data["is_mock_data"] is True
    assert "ATTENTION: Current ERP data source is MOCK SYNTHETIC GENERATOR" in data["warning"]


@pytest.mark.asyncio
async def test_subscription_sync_pipeline(client: AsyncClient):
    """Test full execution of subscription ingestion pipeline."""
    response = await client.post(
        "/api/v1/ingestion/trigger/subscription_sync",
        json={"limit": 50, "force_full_refresh": True},
    )
    assert response.status_code == 200

    # Verify mock safety response headers
    assert response.headers.get("x-data-source") == "MOCK_GENERATOR"
    assert response.headers.get("x-mock-warning") == "DO_NOT_USE_IN_PRODUCTION"

    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["job_name"] == "subscription_sync"
    assert data["is_mock_data"] is True
    assert data["source_type"] == "MOCK_GENERATOR"
    assert data["status"] == "SUCCESS"
    assert data["rows_extracted"] > 0
    assert data["rows_staged"] > 0
    assert data["rows_dimension"] >= 0
    assert data["rows_fact"] > 0
    assert data["rows_features"] > 0


@pytest.mark.asyncio
async def test_billing_sync_pipeline(client: AsyncClient):
    """Test full execution of billing & payment ingestion pipeline."""
    response = await client.post(
        "/api/v1/ingestion/trigger/billing_sync",
        json={"limit": 50, "force_full_refresh": True},
    )
    assert response.status_code == 200
    assert response.headers.get("x-data-source") == "MOCK_GENERATOR"

    payload = response.json()
    assert payload["success"] is True
    data = payload["data"]
    assert data["job_name"] == "billing_sync"
    assert data["is_mock_data"] is True
    assert data["source_type"] == "MOCK_GENERATOR"
    assert data["status"] == "SUCCESS"
    assert data["rows_staged"] > 0
    assert data["rows_fact"] > 0


@pytest.mark.asyncio
async def test_subscription_sync_idempotency(client: AsyncClient):
    """Verify running the pipeline multiple times does not produce duplicate key errors."""
    resp1 = await client.post(
        "/api/v1/ingestion/trigger/subscription_sync",
        json={"limit": 30, "force_full_refresh": False},
    )
    assert resp1.status_code == 200

    resp2 = await client.post(
        "/api/v1/ingestion/trigger/subscription_sync",
        json={"limit": 30, "force_full_refresh": False},
    )
    assert resp2.status_code == 200
    assert resp2.json()["success"] is True


import random


@pytest.mark.asyncio
async def test_scd_type_2_history_tracking():
    """Verify Slowly Changing Dimension Type 2 correctly closes old version and inserts new."""
    test_cust_id = random.randint(700000, 899999)
    day_1 = date(2026, 1, 1)
    day_2 = date(2026, 6, 1)

    async with async_session_factory() as session:
        # Initial version
        initial_record = [{
            "customer_id": test_cust_id,
            "customer_name": "Test Customer SCD2",
            "city": "Jakarta Barat",
            "installation_date": day_1,
            "status": "ACTIVE",
            "source_updated_at": datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
        }]
        await sync_dim_customer_scd2(session, initial_record, snapshot_date=day_1)

        # Check version 1
        q1 = select(DimCustomer).where(col(DimCustomer.customer_id) == test_cust_id)
        res1 = await session.execute(q1)
        records_v1 = res1.scalars().all()
        assert len(records_v1) == 1
        assert records_v1[0].is_current is True
        assert records_v1[0].status == "ACTIVE"
        assert records_v1[0].valid_to is None

        # Status changes to SUSPENDED (triggers SCD Type 2)
        changed_record = [{
            "customer_id": test_cust_id,
            "customer_name": "Test Customer SCD2",
            "city": "Jakarta Barat",
            "installation_date": day_1,
            "status": "SUSPENDED",
            "source_updated_at": datetime(2026, 6, 1, 10, 0, tzinfo=timezone.utc),
        }]
        await sync_dim_customer_scd2(session, changed_record, snapshot_date=day_2)

        # Verify two versions exist now
        q2 = select(DimCustomer).where(col(DimCustomer.customer_id) == test_cust_id).order_by(col(DimCustomer.customer_key))
        res2 = await session.execute(q2)
        records_v2 = res2.scalars().all()
        assert len(records_v2) == 2

        old_v = [r for r in records_v2 if not r.is_current][0]
        new_v = [r for r in records_v2 if r.is_current][0]

        # Old version closed out
        assert old_v.status == "ACTIVE"
        assert old_v.valid_to == day_2
        assert old_v.is_current is False

        # New active version
        assert new_v.status == "SUSPENDED"
        assert new_v.valid_from == day_2
        assert new_v.valid_to is None
        assert new_v.is_current is True


@pytest.mark.asyncio
async def test_batch_history_and_quality_reports(client: AsyncClient):
    """Verify batch history lists [MOCK] tag and quality reports record audit results."""
    hist_resp = await client.get("/api/v1/ingestion/history?limit=10")
    assert hist_resp.status_code == 200
    hist_data = hist_resp.json()["data"]
    assert len(hist_data) > 0
    first_batch = hist_data[0]
    assert first_batch["is_mock_data"] is True
    assert "[MOCK]" in first_batch["status"]

    dq_resp = await client.get("/api/v1/ingestion/quality-reports?limit=10")
    assert dq_resp.status_code == 200
    dq_data = dq_resp.json()["data"]
    assert len(dq_data) > 0
    assert dq_data[0]["status"] == "PASS"


@pytest.mark.asyncio
async def test_scheduler_schedules_endpoint(client: AsyncClient):
    """Verify scheduler endpoint returns registered cron tasks."""
    from app.ingestion.scheduler import start_scheduler
    start_scheduler()

    sched_resp = await client.get("/api/v1/ingestion/schedules")
    assert sched_resp.status_code == 200
    sched_data = sched_resp.json()["data"]
    assert isinstance(sched_data, list)
    job_ids = [j["id"] for j in sched_data]
    assert "daily_subscription_sync" in job_ids
    assert "daily_billing_sync" in job_ids
