import asyncio
from pathlib import Path
import shutil
import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import async_session_factory, engine
from app.ml.inference.churn_predictor import ChurnInferenceService
from app.ml.registry import (
    ARTIFACTS_ROOT_DIR,
    get_active_model_metadata,
    list_available_models,
    reload_active_model,
)
from app.ml.training.train_churn import train_customer_churn_model


@pytest_asyncio.fixture(autouse=True)
async def cleanup_mlops_artifacts_and_db():
    """Fixture to ensure the repository and database remain 100% clean before and after every test."""
    # Pre-clean
    _purge_artifacts()
    await _truncate_prediction_table()
    reload_active_model()

    yield

    # Post-clean (Teardown)
    _purge_artifacts()
    await _truncate_prediction_table()
    reload_active_model()


def _purge_artifacts():
    """Remove all model version directories and active_model.json, preserving only .gitkeep."""
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
        gitkeep.write_text("# Marker file to preserve directory structure in Git while ignoring binary model artifacts\n")


async def _truncate_prediction_table():
    """Truncate prediction table to leave no dummy prediction records in database."""
    try:
        async with engine.begin() as conn:
            await conn.execute(text("TRUNCATE TABLE feature_store.prediction_customer_churn CASCADE;"))
    except Exception:
        pass


@pytest.mark.asyncio
async def test_real_mlops_training_and_lifecycle():
    """Test full real MLOps lifecycle: data loading, XGBoost training, evaluation, versioning, and switching."""
    async with async_session_factory() as session:
        # 1. Train first model version
        v1_result = await train_customer_churn_model(
            session=session,
            model_version="test_v1.0.0",
            hyperparameters={"n_estimators": 50, "max_depth": 3},
            test_size_ratio=0.2,
            set_as_active=True,
        )

        assert v1_result["status"] == "SUCCESS"
        assert v1_result["model_version"] == "test_v1.0.0"
        assert "roc_auc" in v1_result["metrics"]
        assert 0.5 <= v1_result["metrics"]["roc_auc"] <= 1.0
        assert len(v1_result["top_global_features"]) > 0

        # Verify active manifest
        active_meta = get_active_model_metadata()
        assert active_meta is not None
        assert active_meta["model_version"] == "test_v1.0.0"

        # 2. Train second model version with upgraded parameters
        v2_result = await train_customer_churn_model(
            session=session,
            model_version="test_v2.0.0",
            hyperparameters={"n_estimators": 60, "max_depth": 4},
            test_size_ratio=0.2,
            set_as_active=True,
        )

        assert v2_result["status"] == "SUCCESS"
        assert v2_result["model_version"] == "test_v2.0.0"

        # Verify active version switched to v2.0.0
        active_meta_v2 = get_active_model_metadata()
        assert active_meta_v2["model_version"] == "test_v2.0.0"

        # Verify version registry lists both releases
        available = list_available_models()
        versions = [m["model_version"] for m in available]
        assert "test_v1.0.0" in versions
        assert "test_v2.0.0" in versions


@pytest.mark.asyncio
async def test_real_mlops_inference_and_explainability():
    """Test batch prediction, explainability factors, priority ranking, and idempotency using real pipeline."""
    async with async_session_factory() as session:
        # 1. Train model to ensure active model exists
        await train_customer_churn_model(
            session=session,
            model_version="test_v1.0.0",
            set_as_active=True,
        )
        reload_active_model()

        # 2. Run real batch prediction
        batch_res = await ChurnInferenceService.predict_batch(
            session=session,
            snapshot_date=None,  # Resolves latest snapshot
            force_refresh=True,
        )

        assert batch_res["total_evaluated"] > 0
        assert batch_res["rows_saved"] == batch_res["total_evaluated"]
        assert 0.0 <= batch_res["average_churn_probability"] <= 1.0

        # 3. Test Idempotency: re-running batch prediction must not duplicate records
        batch_res_repeat = await ChurnInferenceService.predict_batch(
            session=session,
            snapshot_date=None,
            force_refresh=True,
        )
        assert batch_res_repeat["rows_saved"] == batch_res["rows_saved"]

        # 4. Fetch high-risk customers with explainability
        high_risk_list = await ChurnInferenceService.get_high_risk_customers(
            session=session,
            limit=5,
            min_probability=0.0,  # Grab top customers
        )
        assert len(high_risk_list) > 0

        top_customer = high_risk_list[0]
        assert "customer_id" in top_customer
        assert "churn_probability" in top_customer
        assert "risk_level" in top_customer
        assert "top_risk_factors" in top_customer
        assert isinstance(top_customer["top_risk_factors"], list)

        # 5. Fetch individual customer profile
        cid = top_customer["customer_id"]
        single_res = await ChurnInferenceService.get_customer_prediction(session, customer_id=cid)
        assert single_res is not None
        assert single_res["customer_id"] == cid
        assert single_res["risk_tier_rank"] == 1
