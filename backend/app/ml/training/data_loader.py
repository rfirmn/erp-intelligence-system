from datetime import date
import logging
from typing import Dict, List, Optional, Tuple
import pandas as pd
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.ml.training.preprocessor import ALL_FEATURE_COLUMNS
from app.ml.training.synthetic_labels import ensure_churn_labels
from app.models.features import FeatureCustomerChurn
from app.models.labels import LabelChurnEvent

logger = logging.getLogger("erp_ml.data_loader")


async def load_churn_training_data(
    session: AsyncSession,
    auto_generate_labels_if_empty: bool = True,
    test_size_ratio: float = 0.2,
) -> Tuple[pd.DataFrame, pd.Series, pd.DataFrame, pd.Series, Dict[str, any]]:
    """Load training dataset for Customer Churn prediction with anti-leakage temporal split.
    
    Returns:
        X_train, y_train, X_val, y_val, metadata
    """
    # 1. Check if labels exist; if not and auto_generate enabled, synthesize from latest features
    count_label_q = select(col(LabelChurnEvent.customer_id))
    label_res = await session.execute(count_label_q)
    existing_labels = label_res.fetchall()

    if not existing_labels and auto_generate_labels_if_empty:
        # Determine existing snapshot dates
        dates_q = select(FeatureCustomerChurn.snapshot_date).distinct()
        dates_res = await session.execute(dates_q)
        snapshot_dates = [d[0] for d in dates_res.fetchall()]

        for s_date in snapshot_dates:
            await ensure_churn_labels(session, target_snapshot_date=s_date)

    # 2. Query Joined Features and Labels (Strict Anti-Leakage Gate)
    join_query = (
        select(
            col(FeatureCustomerChurn.snapshot_date),
            col(FeatureCustomerChurn.customer_id),
            col(FeatureCustomerChurn.tenure_months),
            col(FeatureCustomerChurn.monthly_fee_current),
            col(FeatureCustomerChurn.package_speed_mbps),
            col(FeatureCustomerChurn.late_payment_count_3m),
            col(FeatureCustomerChurn.late_payment_count_6m),
            col(FeatureCustomerChurn.avg_payment_delay_days_3m),
            col(FeatureCustomerChurn.payment_status_trend),
            col(FeatureCustomerChurn.downgrade_flag_6m),
            col(LabelChurnEvent.label_window_start),
            col(LabelChurnEvent.churned),
        )
        .join(
            LabelChurnEvent,
            (col(FeatureCustomerChurn.customer_id) == col(LabelChurnEvent.customer_id))
            & (col(FeatureCustomerChurn.snapshot_date) == col(LabelChurnEvent.feature_snapshot_date)),
        )
        .where(col(LabelChurnEvent.label_window_start) >= col(FeatureCustomerChurn.snapshot_date))
        .order_by(col(FeatureCustomerChurn.snapshot_date).asc(), col(FeatureCustomerChurn.customer_id).asc())
    )

    result = await session.execute(join_query)
    rows = result.fetchall()

    if not rows:
        raise ValueError(
            "Tidak ditemukan data fitur & label yang valid untuk pelatihan model churn. "
            "Pastikan pipeline ingestion (Fase 2) telah menghasilkan feature_customer_churn."
        )

    # 3. Construct pandas DataFrame
    data_dicts = []
    for r in rows:
        data_dicts.append({
            "snapshot_date": r[0],
            "customer_id": r[1],
            "tenure_months": float(r[2]) if r[2] is not None else None,
            "monthly_fee_current": float(r[3]) if r[3] is not None else None,
            "package_speed_mbps": int(r[4]) if r[4] is not None else None,
            "late_payment_count_3m": int(r[5]) if r[5] is not None else 0,
            "late_payment_count_6m": int(r[6]) if r[6] is not None else 0,
            "avg_payment_delay_days_3m": float(r[7]) if r[7] is not None else 0.0,
            "payment_status_trend": str(r[8]) if r[8] else "STABLE",
            "downgrade_flag_6m": bool(r[9]) if r[9] is not None else False,
            "churned": 1 if r[11] else 0,
        })

    df = pd.DataFrame(data_dicts)
    logger.info(f"Loaded {len(df)} feature-label pairs for Churn model training.")

    # 4. Temporal Split (Anti-Leakage: Train on earlier periods, Validate on later periods)
    n_total = len(df)
    n_train = max(int(n_total * (1.0 - test_size_ratio)), 1)
    
    # If single snapshot date, split sequentially by index
    df_train = df.iloc[:n_train].copy()
    df_val = df.iloc[n_train:].copy() if n_train < n_total else df.iloc[:n_train].copy()

    X_train = df_train[ALL_FEATURE_COLUMNS]
    y_train = df_train["churned"]

    X_val = df_val[ALL_FEATURE_COLUMNS]
    y_val = df_val["churned"]

    metadata = {
        "total_samples": n_total,
        "train_samples": len(X_train),
        "val_samples": len(X_val),
        "positive_class_train": int(y_train.sum()),
        "positive_class_val": int(y_val.sum()),
        "churn_rate_train": round(float(y_train.mean()), 4),
        "churn_rate_val": round(float(y_val.mean()), 4),
        "feature_columns": ALL_FEATURE_COLUMNS,
    }

    logger.info(
        f"Temporal split completed: Train={len(X_train)} (churn={metadata['positive_class_train']}), "
        f"Val={len(X_val)} (churn={metadata['positive_class_val']})"
    )

    return X_train, y_train, X_val, y_val, metadata
