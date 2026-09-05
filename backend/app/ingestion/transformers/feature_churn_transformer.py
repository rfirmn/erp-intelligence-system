from datetime import date
import logging
from typing import Any, Dict, List
import uuid
from sqlmodel import col
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dimensions import DimCustomer, DimPackage
from app.models.facts import FactBillingMonthly, FactSubscriptionSnapshot
from app.models.features import FeatureCustomerChurn

logger = logging.getLogger("erp_ingestion.transformers.feature_churn")


async def build_feature_customer_churn(
    session: AsyncSession,
    snapshot_date: date,
    batch_id: uuid.UUID,
) -> int:
    """Compile wide denormalized ML-ready feature table for customer churn prediction."""
    # 1. Fetch current subscription snapshot per customer
    query = (
        select(
            col(DimCustomer.customer_id),
            col(FactSubscriptionSnapshot.tenure_days),
            col(FactSubscriptionSnapshot.monthly_fee),
            col(DimPackage.speed_mbps),
            col(DimCustomer.customer_key),
        )
        .join(DimCustomer, col(DimCustomer.customer_key) == col(FactSubscriptionSnapshot.customer_key))
        .outerjoin(DimPackage, col(DimPackage.package_key) == col(FactSubscriptionSnapshot.package_key))
        .where(col(FactSubscriptionSnapshot.snapshot_date) == snapshot_date)
    )

    result = await session.execute(query)
    cust_snapshots = result.fetchall()

    if not cust_snapshots:
        logger.warning(f"No subscription snapshots found on {snapshot_date} to build churn features.")
        return 0

    feature_rows: Dict[Any, Dict[str, Any]] = {}
    for cid, tenure_days, fee, speed, ckey in cust_snapshots:
        # 2. Query billing history (last 3 and 6 months) for this customer
        billing_query = (
            select(col(FactBillingMonthly.days_late), col(FactBillingMonthly.payment_status))
            .where(col(FactBillingMonthly.customer_key) == ckey)
            .order_by(col(FactBillingMonthly.invoice_period).desc())
            .limit(6)
        )
        billing_res = await session.execute(billing_query)
        billing_history = billing_res.fetchall()

        late_3m = sum(1 for b in billing_history[:3] if (b[0] or 0) > 0 or b[1] != "PAID")
        late_6m = sum(1 for b in billing_history if (b[0] or 0) > 0 or b[1] != "PAID")

        delays_3m = [b[0] for b in billing_history[:3] if b[0] is not None and b[0] > 0]
        avg_delay_3m = round(sum(delays_3m) / len(delays_3m), 1) if delays_3m else 0.0

        if late_3m > 1:
            trend = "WORSENING"
        elif late_3m == 0:
            trend = "STABLE"
        else:
            trend = "IMPROVING"

        tenure_months = round((tenure_days or 0) / 30.0, 1)

        feature_rows[(snapshot_date, cid)] = {
            "snapshot_date": snapshot_date,
            "customer_id": cid,
            "tenure_months": tenure_months,
            "monthly_fee_current": fee,
            "package_speed_mbps": speed or 30,
            "late_payment_count_3m": late_3m,
            "late_payment_count_6m": late_6m,
            "avg_payment_delay_days_3m": avg_delay_3m,
            "payment_status_trend": trend,
            "downgrade_flag_6m": False,
            "batch_id": batch_id,
        }

    feature_records = list(feature_rows.values())
    if not feature_records:
        return 0

    # 3. PostgreSQL Idempotent Upsert
    stmt = pg_insert(FeatureCustomerChurn).values(feature_records)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["snapshot_date", "customer_id"],
        set_={
            "tenure_months": stmt.excluded.tenure_months,
            "monthly_fee_current": stmt.excluded.monthly_fee_current,
            "package_speed_mbps": stmt.excluded.package_speed_mbps,
            "late_payment_count_3m": stmt.excluded.late_payment_count_3m,
            "late_payment_count_6m": stmt.excluded.late_payment_count_6m,
            "avg_payment_delay_days_3m": stmt.excluded.avg_payment_delay_days_3m,
            "payment_status_trend": stmt.excluded.payment_status_trend,
            "downgrade_flag_6m": stmt.excluded.downgrade_flag_6m,
            "batch_id": stmt.excluded.batch_id,
        },
    )

    await session.execute(upsert_stmt)
    await session.commit()
    logger.info(f"Loaded {len(feature_rows)} ML feature rows into feature_store.feature_customer_churn")
    return len(feature_rows)
