from datetime import date
import logging
from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import desc, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.core.datetime_utils import utc_now
from app.ml.inference.explainer import explain_customer_risk
from app.ml.registry import get_active_model_metadata, get_active_model_pipeline
from app.ml.training.preprocessor import ALL_FEATURE_COLUMNS
from app.models.dimensions import DimCustomer
from app.models.features import FeatureCustomerChurn
from app.models.metadata import DataQualityLog
from app.models.predictions import PredictionCustomerChurn

logger = logging.getLogger("erp_ml.predictor")


class ChurnInferenceService:
    """Production inference engine for Customer Churn Risk prediction."""

    @staticmethod
    async def predict_batch(
        session: AsyncSession,
        snapshot_date: Optional[date] = None,
        force_refresh: bool = True,
    ) -> Dict[str, Any]:
        """Execute batch inference for a snapshot date and persist results to prediction_customer_churn."""
        pipeline = get_active_model_pipeline()
        active_meta = get_active_model_metadata() or {}
        model_version = active_meta.get("model_version", "1.0.0")

        # 1. Resolve snapshot_date (use latest if not specified)
        if snapshot_date is None:
            latest_date_q = select(func.max(FeatureCustomerChurn.snapshot_date))
            latest_date_res = await session.execute(latest_date_q)
            snapshot_date = latest_date_res.scalar()

            if snapshot_date is None:
                raise ValueError("Tidak ada snapshot fitur yang tersedia di feature_store.feature_customer_churn.")

        logger.info(f"Executing batch churn inference on snapshot {snapshot_date} with model v{model_version}...")

        # 2. Fetch all feature records on this snapshot
        features_query = (
            select(
                col(FeatureCustomerChurn.customer_id),
                col(FeatureCustomerChurn.tenure_months),
                col(FeatureCustomerChurn.monthly_fee_current),
                col(FeatureCustomerChurn.package_speed_mbps),
                col(FeatureCustomerChurn.late_payment_count_3m),
                col(FeatureCustomerChurn.late_payment_count_6m),
                col(FeatureCustomerChurn.avg_payment_delay_days_3m),
                col(FeatureCustomerChurn.payment_status_trend),
                col(FeatureCustomerChurn.downgrade_flag_6m),
            )
            .where(col(FeatureCustomerChurn.snapshot_date) == snapshot_date)
            .order_by(col(FeatureCustomerChurn.customer_id).asc())
        )

        features_res = await session.execute(features_query)
        rows = features_res.fetchall()

        if not rows:
            logger.warning(f"No customer features found for snapshot date: {snapshot_date}")
            return {
                "snapshot_date": str(snapshot_date),
                "model_version": model_version,
                "total_evaluated": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
                "average_churn_probability": 0.0,
                "rows_saved": 0,
            }

        # 3. Assemble DataFrame for vectorized inference
        records = []
        raw_feature_dicts = []
        for r in rows:
            f_dict = {
                "customer_id": r[0],
                "tenure_months": float(r[1]) if r[1] is not None else None,
                "monthly_fee_current": float(r[2]) if r[2] is not None else None,
                "package_speed_mbps": int(r[3]) if r[3] is not None else None,
                "late_payment_count_3m": int(r[4]) if r[4] is not None else 0,
                "late_payment_count_6m": int(r[5]) if r[5] is not None else 0,
                "avg_payment_delay_days_3m": float(r[6]) if r[6] is not None else 0.0,
                "payment_status_trend": str(r[7]) if r[7] else "STABLE",
                "downgrade_flag_6m": bool(r[8]) if r[8] is not None else False,
            }
            records.append(f_dict)
            raw_feature_dicts.append(f_dict)

        df = pd.DataFrame(records)

        # 4. Predict probabilities
        probabilities = pipeline.predict_proba(df[ALL_FEATURE_COLUMNS])[:, 1]
        df["churn_probability"] = probabilities

        # Sort descending by probability to assign priority ranks
        df = df.sort_values(by="churn_probability", ascending=False).reset_index(drop=True)
        df["risk_tier_rank"] = df.index + 1

        # 5. Build DB records with explainability factors
        prediction_db_records: List[Dict[str, Any]] = []
        high_risk_count = 0
        med_risk_count = 0
        low_risk_count = 0

        for idx, row in df.iterrows():
            prob = float(row["churn_probability"])
            if prob >= 0.70:
                risk_level = "HIGH"
                high_risk_count += 1
            elif prob >= 0.30:
                risk_level = "MEDIUM"
                med_risk_count += 1
            else:
                risk_level = "LOW"
                low_risk_count += 1

            factors = explain_customer_risk(row.to_dict())

            prediction_db_records.append({
                "snapshot_date": snapshot_date,
                "customer_id": int(row["customer_id"]),
                "churn_probability": round(prob, 4),
                "risk_level": risk_level,
                "risk_tier_rank": int(row["risk_tier_rank"]),
                "top_risk_factors": factors,
                "model_version": model_version,
                "created_at": utc_now(),
            })

        # 6. Idempotent Upsert into feature_store.prediction_customer_churn
        stmt = pg_insert(PredictionCustomerChurn).values(prediction_db_records)
        upsert_stmt = stmt.on_conflict_do_update(
            index_elements=["snapshot_date", "customer_id"],
            set_={
                "churn_probability": stmt.excluded.churn_probability,
                "risk_level": stmt.excluded.risk_level,
                "risk_tier_rank": stmt.excluded.risk_tier_rank,
                "top_risk_factors": stmt.excluded.top_risk_factors,
                "model_version": stmt.excluded.model_version,
                "created_at": stmt.excluded.created_at,
            },
        )

        await session.execute(upsert_stmt)

        # 7. Basic Drift & Quality Logging
        avg_prob = round(float(df["churn_probability"].mean()), 4)
        dq_log = DataQualityLog(
            check_name="batch_churn_prediction_audit",
            table_name="prediction_customer_churn",
            status="PASS" if high_risk_count < len(df) * 0.5 else "WARN",
            details=(
                f"Evaluated {len(df)} customers. High={high_risk_count}, "
                f"Med={med_risk_count}, Low={low_risk_count}, MeanProb={avg_prob}"
            ),
        )
        session.add(dq_log)
        await session.commit()

        logger.info(
            f"Completed batch inference for {len(df)} customers. "
            f"High Risk: {high_risk_count}, Medium: {med_risk_count}, Low: {low_risk_count}"
        )

        return {
            "snapshot_date": str(snapshot_date),
            "model_version": model_version,
            "total_evaluated": len(df),
            "high_risk_count": high_risk_count,
            "medium_risk_count": med_risk_count,
            "low_risk_count": low_risk_count,
            "average_churn_probability": avg_prob,
            "rows_saved": len(prediction_db_records),
        }

    @staticmethod
    async def get_high_risk_customers(
        session: AsyncSession,
        limit: int = 20,
        min_probability: float = 0.70,
        snapshot_date: Optional[date] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve top high-risk customers joined with customer identity from dim_customer."""
        # If snapshot_date is None, find latest snapshot
        if snapshot_date is None:
            latest_date_q = select(func.max(PredictionCustomerChurn.snapshot_date))
            latest_res = await session.execute(latest_date_q)
            snapshot_date = latest_res.scalar()

        if snapshot_date is None:
            return []

        query = (
            select(
                col(PredictionCustomerChurn.customer_id),
                col(PredictionCustomerChurn.snapshot_date),
                col(PredictionCustomerChurn.churn_probability),
                col(PredictionCustomerChurn.risk_level),
                col(PredictionCustomerChurn.risk_tier_rank),
                col(PredictionCustomerChurn.top_risk_factors),
                col(PredictionCustomerChurn.model_version),
                col(DimCustomer.customer_name),
                col(DimCustomer.city),
                col(DimCustomer.status),
            )
            .outerjoin(
                DimCustomer,
                (col(DimCustomer.customer_id) == col(PredictionCustomerChurn.customer_id))
                & (col(DimCustomer.is_current) == True),
            )
            .where(
                col(PredictionCustomerChurn.snapshot_date) == snapshot_date,
                col(PredictionCustomerChurn.churn_probability) >= min_probability,
            )
            .order_by(col(PredictionCustomerChurn.churn_probability).desc())
            .limit(limit)
        )

        result = await session.execute(query)
        rows = result.fetchall()

        items = []
        for r in rows:
            items.append({
                "customer_id": r[0],
                "customer_name": r[7] or f"Customer #{r[0]}",
                "city": r[8] or "Unknown",
                "customer_status": r[9] or "ACTIVE",
                "snapshot_date": str(r[1]),
                "churn_probability": float(r[2]),
                "risk_level": r[3],
                "risk_tier_rank": r[4],
                "top_risk_factors": r[5] or [],
                "model_version": r[6],
            })

        return items

    @staticmethod
    async def get_customer_prediction(
        session: AsyncSession,
        customer_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve latest churn prediction and feature context for an individual customer."""
        query = (
            select(
                col(PredictionCustomerChurn.customer_id),
                col(PredictionCustomerChurn.snapshot_date),
                col(PredictionCustomerChurn.churn_probability),
                col(PredictionCustomerChurn.risk_level),
                col(PredictionCustomerChurn.risk_tier_rank),
                col(PredictionCustomerChurn.top_risk_factors),
                col(PredictionCustomerChurn.model_version),
                col(DimCustomer.customer_name),
                col(DimCustomer.city),
                col(DimCustomer.status),
            )
            .outerjoin(
                DimCustomer,
                (col(DimCustomer.customer_id) == col(PredictionCustomerChurn.customer_id))
                & (col(DimCustomer.is_current) == True),
            )
            .where(col(PredictionCustomerChurn.customer_id) == customer_id)
            .order_by(col(PredictionCustomerChurn.snapshot_date).desc())
            .limit(1)
        )

        result = await session.execute(query)
        row = result.fetchone()

        if not row:
            return None

        return {
            "customer_id": row[0],
            "customer_name": row[7] or f"Customer #{row[0]}",
            "city": row[8] or "Unknown",
            "customer_status": row[9] or "ACTIVE",
            "snapshot_date": str(row[1]),
            "churn_probability": float(row[2]),
            "risk_level": row[3],
            "risk_tier_rank": row[4],
            "top_risk_factors": row[5] or [],
            "model_version": row[6],
        }
