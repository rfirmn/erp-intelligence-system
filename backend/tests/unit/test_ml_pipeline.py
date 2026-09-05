import os
import pytest
import pandas as pd
import numpy as np
from app.ml.training.preprocessor import build_feature_preprocessor, ALL_FEATURE_COLUMNS
from app.ml.models.churn_xgboost import ChurnXGBoostModel
from app.ml.inference.explainer import explain_customer_risk
from app.ml.registry import get_active_model_metadata, list_available_models


def test_preprocessor_transformation():
    """Verify that the ColumnTransformer handles nulls, ordinal categories, and outputs valid numeric matrices."""
    preprocessor = build_feature_preprocessor()

    sample_df = pd.DataFrame([
        {
            "tenure_months": 12.5,
            "monthly_fee_current": 385000.0,
            "package_speed_mbps": 50,
            "late_payment_count_3m": 2,
            "late_payment_count_6m": 3,
            "avg_payment_delay_days_3m": 12.0,
            "payment_status_trend": "WORSENING",
            "downgrade_flag_6m": True,
        },
        {
            "tenure_months": None,  # Should be imputed
            "monthly_fee_current": None,
            "package_speed_mbps": None,
            "late_payment_count_3m": 0,
            "late_payment_count_6m": 0,
            "avg_payment_delay_days_3m": 0.0,
            "payment_status_trend": "IMPROVING",
            "downgrade_flag_6m": False,
        },
    ])

    transformed = preprocessor.fit_transform(sample_df)
    assert transformed.shape == (2, len(ALL_FEATURE_COLUMNS))
    assert not np.isnan(transformed).any(), "Preprocessed matrix must not contain any NaN values."


def test_churn_xgboost_model_fit_and_predict():
    """Verify that ChurnXGBoostModel trains properly and outputs probabilities bounded in [0, 1]."""
    np.random.seed(42)
    X = np.random.randn(50, 8)
    y = np.array([1 if i % 4 == 0 else 0 for i in range(50)])  # Imbalanced 25% churn

    model = ChurnXGBoostModel(n_estimators=10, max_depth=3)
    model.fit(X, y)

    preds = model.predict(X)
    probs = model.predict_proba(X)

    assert len(preds) == 50
    assert probs.shape == (50, 2)
    assert np.all(probs >= 0.0) and np.all(probs <= 1.0)
    assert len(model.feature_importances_) == 8


def test_customer_risk_explainer():
    """Verify that explain_customer_risk produces insightful, grounded statements for high-risk customers."""
    risky_features = {
        "late_payment_count_3m": 3,
        "late_payment_count_6m": 4,
        "avg_payment_delay_days_3m": 18.5,
        "payment_status_trend": "WORSENING",
        "tenure_months": 4.0,
        "monthly_fee_current": 1250000.0,
    }

    drivers = explain_customer_risk(risky_features)
    assert len(drivers) > 0
    assert len(drivers) <= 3

    features_in_drivers = [d["feature"] for d in drivers]
    assert "late_payment_count_3m" in features_in_drivers or "payment_status_trend" in features_in_drivers
    for d in drivers:
        assert "description" in d
        assert "severity" in d
        assert "impact" in d


def test_ml_code_config_and_presets():
    """Verify that ml_config enables dynamic code-first experimentation without .env dependencies."""
    from app.ml.config import HYPERPARAMETER_PRESETS, ml_config

    # 1. Test defaults
    default_hp = ml_config.resolve_hyperparameters()
    assert default_hp["n_estimators"] == 100
    assert default_hp["max_depth"] == 4
    assert default_hp["learning_rate"] == 0.05

    # 2. Test presets
    fast_hp = ml_config.resolve_hyperparameters(preset="fast_prototype")
    assert fast_hp["n_estimators"] == 30
    assert fast_hp["max_depth"] == 3
    assert fast_hp["learning_rate"] == 0.1

    deep_hp = ml_config.resolve_hyperparameters(preset="deep_tuned")
    assert deep_hp["n_estimators"] == 250
    assert deep_hp["max_depth"] == 6

    # 3. Test dynamic overrides
    custom_hp = ml_config.resolve_hyperparameters(
        preset="fast_prototype",
        overrides={"n_estimators": 45, "learning_rate": 0.08},
    )
    assert custom_hp["n_estimators"] == 45
    assert custom_hp["learning_rate"] == 0.08
    assert custom_hp["max_depth"] == 3

    # 4. Test risk categorization
    assert ml_config.risk_thresholds.categorize(0.85) == "HIGH"
    assert ml_config.risk_thresholds.categorize(0.50) == "MEDIUM"
    assert ml_config.risk_thresholds.categorize(0.15) == "LOW"

    # 5. Test tuning search space
    assert "n_estimators" in ml_config.tuning.param_grid
    assert "max_depth" in ml_config.tuning.param_grid
    assert len(ml_config.tuning.param_grid["n_estimators"]) > 1
