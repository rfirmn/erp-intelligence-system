from pathlib import Path
import shutil
import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text

from app.core.session import engine
from app.main import app
from app.ml.registry import ARTIFACTS_ROOT_DIR, reload_active_model
from app.schemas.ml import (
    BatchPredictionResponse,
    CustomerRiskProfile,
    ModelMetadataResponse,
    ModelTrainResponse,
)


def _purge_artifacts():
    if not ARTIFACTS_ROOT_DIR.exists():
        return
    for item in ARTIFACTS_ROOT_DIR.iterdir():
        if item.name == ".gitkeep":
            continue
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        elif item.is_file():
            item.unlink(missing_ok=True)
    gitkeep = ARTIFACTS_ROOT_DIR / ".gitkeep"
    if not gitkeep.exists():
        gitkeep.write_text("# Marker file\n")


async def _truncate_prediction_table():
    try:
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE feature_store.prediction_customer_churn CASCADE;"))
    except Exception:
        pass


@pytest_asyncio.fixture(autouse=True)
async def cleanup_after_test():
    _purge_artifacts()
    await _truncate_prediction_table()
    reload_active_model()
    yield
    _purge_artifacts()
    await _truncate_prediction_table()
    reload_active_model()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_ml_end_to_end_flow(client: AsyncClient):
    # 1. Trigger Model Training
    train_resp = await client.post(
        "/api/v1/ml/models/churn/train",
        json={
            "model_version": "1.0.0",
            "test_size_ratio": 0.2,
            "set_as_active": True,
        },
    )
    assert train_resp.status_code == 200
    train_payload = train_resp.json()
    assert train_payload["success"] is True
    assert train_payload["data"]["status"] == "SUCCESS"
    assert "roc_auc" in train_payload["data"]["metrics"]
    assert len(train_payload["data"]["top_global_features"]) > 0

    # 2. Query Active Model Metadata
    meta_resp = await client.get("/api/v1/ml/models/churn/metadata")
    assert meta_resp.status_code == 200
    meta_payload = meta_resp.json()
    assert meta_payload["success"] is True
    assert meta_payload["data"]["model_version"] == "1.0.0"
    assert meta_payload["data"]["is_active"] is True
    assert "late_payment_count_3m" in meta_payload["data"]["features"]

    # 3. Trigger Batch Prediction on Latest Snapshot
    batch_resp = await client.post(
        "/api/v1/ml/predictions/churn/batch",
        json={"force_refresh": True},
    )
    assert batch_resp.status_code == 200
    batch_payload = batch_resp.json()
    assert batch_payload["success"] is True
    assert batch_payload["data"]["total_evaluated"] > 0
    assert batch_payload["data"]["rows_saved"] > 0
    assert 0.0 <= batch_payload["data"]["average_churn_probability"] <= 1.0

    # 4. Fetch High-Risk Customers
    high_risk_resp = await client.get("/api/v1/ml/predictions/churn/high-risk?limit=10&min_probability=0.0")
    assert high_risk_resp.status_code == 200
    high_risk_payload = high_risk_resp.json()
    assert high_risk_payload["success"] is True
    assert isinstance(high_risk_payload["data"], list)
    assert len(high_risk_payload["data"]) > 0

    first_customer = high_risk_payload["data"][0]
    cust_id = first_customer["customer_id"]
    assert "churn_probability" in first_customer
    assert first_customer["risk_level"] in ("LOW", "MEDIUM", "HIGH")
    assert "top_risk_factors" in first_customer

    # 5. Fetch Individual Customer Risk Profile
    cust_resp = await client.get(f"/api/v1/ml/predictions/churn/customer/{cust_id}")
    assert cust_resp.status_code == 200
    cust_payload = cust_resp.json()
    assert cust_payload["success"] is True
    assert cust_payload["data"]["customer_id"] == cust_id
    assert cust_payload["data"]["model_version"] == "1.0.0"
