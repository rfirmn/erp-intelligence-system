from datetime import date
import logging
from typing import Any, Dict, List
import uuid
from sqlmodel import col
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dimensions import DimCustomer, DimPackage
from app.models.facts import FactSubscriptionSnapshot

logger = logging.getLogger("erp_ingestion.transformers.fact_subscription")


async def load_fact_subscription_snapshot(
    session: AsyncSession,
    records: List[Dict[str, Any]],
    snapshot_date: date,
    batch_id: uuid.UUID,
) -> int:
    """Build and idempotent-upsert daily periodic subscription snapshot facts."""
    if not records:
        return 0

    # 1. Lookup surrogate keys
    cust_keys: Dict[int, int] = {}
    pkg_keys: Dict[int, int] = {}

    cust_res = await session.execute(
        select(col(DimCustomer.customer_id), col(DimCustomer.customer_key)).where(
            col(DimCustomer.is_current) == True
        )
    )
    for cid_val, ckey_val in cust_res.fetchall():
        if cid_val is not None and ckey_val is not None:
            cust_keys[int(cid_val)] = int(ckey_val)

    pkg_res = await session.execute(
        select(col(DimPackage.package_id), col(DimPackage.package_key)).where(
            col(DimPackage.is_current) == True
        )
    )
    for pid_val, pkey_val in pkg_res.fetchall():
        if pid_val is not None and pkey_val is not None:
            pkg_keys[int(pid_val)] = int(pkey_val)

    fact_rows: Dict[Any, Dict[str, Any]] = {}
    for r in records:
        cid = r.get("customer_id")
        if not isinstance(cid, int):
            continue
        ckey = cust_keys.get(cid)
        if not ckey:
            continue

        pid = r.get("package_id")
        pkey = pkg_keys.get(pid) if isinstance(pid, int) else None

        start_d = r.get("start_date") or snapshot_date
        tenure = max(0, (snapshot_date - start_d).days)
        is_act = r.get("status") == "ACTIVE"

        # Key by conflict target to prevent CardinalityViolationError in ON CONFLICT DO UPDATE
        fact_rows[(snapshot_date, ckey)] = {
            "snapshot_date": snapshot_date,
            "customer_key": ckey,
            "package_key": pkey,
            "subscription_status": r.get("status"),
            "tenure_days": tenure,
            "monthly_fee": r.get("monthly_fee"),
            "is_active": is_act,
            "batch_id": batch_id,
        }

    fact_records = list(fact_rows.values())
    if not fact_records:
        return 0

    # 2. PostgreSQL Idempotent Upsert (INSERT ... ON CONFLICT DO UPDATE)
    stmt = pg_insert(FactSubscriptionSnapshot).values(fact_records)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["snapshot_date", "customer_key"],
        set_={
            "package_key": stmt.excluded.package_key,
            "subscription_status": stmt.excluded.subscription_status,
            "tenure_days": stmt.excluded.tenure_days,
            "monthly_fee": stmt.excluded.monthly_fee,
            "is_active": stmt.excluded.is_active,
            "batch_id": stmt.excluded.batch_id,
        },
    )

    await session.execute(upsert_stmt)
    await session.commit()
    logger.info(f"Loaded {len(fact_rows)} facts into feature_store.fact_subscription_snapshot")
    return len(fact_rows)
