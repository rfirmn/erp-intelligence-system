from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import joblib
import numpy as np
import pandas as pd
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.config import ml_config
from app.ml.models.churn_xgboost import ChurnXGBoostModel
from app.ml.training.data_loader import load_churn_training_data
from app.ml.training.preprocessor import ALL_FEATURE_COLUMNS, build_feature_preprocessor

logger = logging.getLogger("erp_ml.training")

ARTIFACTS_ROOT_DIR = ml_config.artifacts_dir


async def train_customer_churn_model(
    session: AsyncSession,
    model_version: Optional[str] = None,
    model_name: Optional[str] = None,
    preset: Optional[str] = None,
    hyperparameters: Optional[Dict[str, Any]] = None,
    test_size_ratio: Optional[float] = None,
    set_as_active: bool = True,
) -> Dict[str, Any]:
    """Orchestrate training of the XGBoost Customer Churn Prediction model."""
    version = model_version or ml_config.model_identity.default_version
    resolved_model_name = model_name or ml_config.model_identity.model_name
    resolved_test_size = (
        test_size_ratio if test_size_ratio is not None else ml_config.training.test_size_ratio
    )
    logger.info(f"Starting training pipeline for model '{resolved_model_name}' version '{version}' (preset={preset})...")

    # 1. Load data with temporal split
    X_train, y_train, X_val, y_val, data_meta = await load_churn_training_data(
        session=session,
        auto_generate_labels_if_empty=ml_config.training.auto_generate_labels_if_empty,
        test_size_ratio=resolved_test_size,
    )

    # 2. Build full Scikit-Learn Pipeline using dynamic hyperparameters
    preprocessor = build_feature_preprocessor()
    params = ml_config.resolve_hyperparameters(preset=preset, overrides=hyperparameters)
    classifier = ChurnXGBoostModel(
        n_estimators=params.get("n_estimators"),
        max_depth=params.get("max_depth"),
        learning_rate=params.get("learning_rate"),
        subsample=params.get("subsample"),
        colsample_bytree=params.get("colsample_bytree"),
        scale_pos_weight=params.get("scale_pos_weight"),
        random_state=params.get("random_state"),
    )

    full_pipeline = Pipeline(
        steps=[
            ("preprocessor", preprocessor),
            ("classifier", classifier),
        ]
    )

    # 3. Fit Pipeline
    full_pipeline.fit(X_train, y_train)

    # 4. Evaluate on Validation Set (Out-of-Time)
    y_prob = full_pipeline.predict_proba(X_val)[:, 1]
    eval_threshold = params.get("threshold", ml_config.risk_thresholds.classification_threshold)
    y_pred = (y_prob >= eval_threshold).astype(int)

    # Calculate metrics with safe edge cases
    try:
        roc_auc = float(roc_auc_score(y_val, y_prob))
        if np.isnan(roc_auc):
            roc_auc = 0.5
    except Exception:
        roc_auc = 0.5

    try:
        pr_auc = float(average_precision_score(y_val, y_prob))
        if np.isnan(pr_auc):
            pr_auc = float(y_val.mean()) if len(y_val) > 0 else 0.0
    except Exception:
        pr_auc = float(y_val.mean()) if len(y_val) > 0 else 0.0

    f1 = float(f1_score(y_val, y_pred, zero_division=0))  # type: ignore
    prec = float(precision_score(y_val, y_pred, zero_division=0))  # type: ignore
    rec = float(recall_score(y_val, y_pred, zero_division=0))  # type: ignore
    brier = float(brier_score_loss(y_val, y_prob))
    conf_mat = confusion_matrix(y_val, y_pred).tolist()

    metrics = {
        "roc_auc": round(roc_auc, 4),
        "pr_auc": round(pr_auc, 4),
        "f1_score": round(f1, 4),
        "precision": round(prec, 4),
        "recall": round(rec, 4),
        "brier_score": round(brier, 4),
        "confusion_matrix": conf_mat,
    }

    # 5. Extract Feature Importance
    try:
        clf_step: ChurnXGBoostModel = full_pipeline.named_steps["classifier"]
        importances = clf_step.feature_importances_
        feature_names = ALL_FEATURE_COLUMNS
        feat_imp_list = [
            {"feature": name, "importance": round(float(imp), 4)}
            for name, imp in sorted(
                zip(feature_names, importances),
                key=lambda x: x[1],
                reverse=True,
            )
        ]
    except Exception as e:
        logger.warning(f"Could not extract feature importances: {e}")
        feat_imp_list = []

    # 6. Save Artifacts to Local Registry
    version_dir = ARTIFACTS_ROOT_DIR / f"{resolved_model_name}_v{version}"
    version_dir.mkdir(parents=True, exist_ok=True)

    pipeline_path = version_dir / "pipeline.joblib"
    metadata_path = version_dir / "metadata.json"
    feat_imp_path = version_dir / "feature_importance.json"

    # Serialize trained pipeline
    joblib.dump(full_pipeline, pipeline_path)

    trained_at_iso = datetime.now(timezone.utc).isoformat()
    metadata_payload = {
        "model_name": resolved_model_name,
        "model_version": version,
        "algorithm": ml_config.model_identity.algorithm,
        "trained_at": trained_at_iso,
        "features": ALL_FEATURE_COLUMNS,
        "hyperparameters": params,
        "dataset": data_meta,
        "metrics": metrics,
        "artifact_rel_path": f"artifacts/{resolved_model_name}_v{version}/pipeline.joblib",
    }

    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata_payload, f, indent=2)

    with open(feat_imp_path, "w", encoding="utf-8") as f:
        json.dump(feat_imp_list, f, indent=2)

    # 7. Update active_model.json pointer if set_as_active
    if set_as_active:
        active_manifest = {
            "active_version": version,
            "model_name": resolved_model_name,
            "activated_at": trained_at_iso,
            "version_dir": str(version_dir),
            "pipeline_path": str(pipeline_path),
            "metrics": metrics,
        }
        with open(ARTIFACTS_ROOT_DIR / "active_model.json", "w", encoding="utf-8") as f:
            json.dump(active_manifest, f, indent=2)
        logger.info(f"Model '{resolved_model_name}' version '{version}' is now active.")

    logger.info(
        f"Churn model '{resolved_model_name}' version '{version}' successfully trained and registered. "
        f"ROC-AUC: {metrics['roc_auc']}, F1: {metrics['f1_score']}"
    )

    return {
        "model_name": resolved_model_name,
        "model_version": version,
        "status": "SUCCESS",
        "trained_at": trained_at_iso,
        "total_samples": len(X_train) + len(X_val),
        "metrics": metrics,
        "top_global_features": feat_imp_list[:10],
        "is_active": set_as_active,
    }
