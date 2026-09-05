from datetime import date
import logging
from typing import Any, Dict, List
import uuid
from sqlmodel import col
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dimensions import DimCustomer
from app.models.facts import FactBillingMonthly

logger = logging.getLogger("erp_ingestion.transformers.fact_billing")


async def load_fact_billing_monthly(
    session: AsyncSession,
    invoices: List[Dict[str, Any]],
    batch_id: uuid.UUID,
) -> int:
    """Build and idempotent-upsert monthly billing facts per customer."""
    if not invoices:
        return 0

    # Lookup surrogate customer keys
    cust_res = await session.execute(
        select(col(DimCustomer.customer_id), col(DimCustomer.customer_key)).where(
            col(DimCustomer.is_current) == True
        )
    )
    cust_keys: Dict[int, int] = {
        int(cid): int(ckey)
        for cid, ckey in cust_res.fetchall()
        if cid is not None and ckey is not None
    }

    fact_rows: Dict[Any, Dict[str, Any]] = {}
    for inv in invoices:
        cid = inv.get("customer_id")
        if not isinstance(cid, int):
            continue
        ckey = cust_keys.get(cid)
        if not ckey:
            continue

        fact_rows[(inv["invoice_period"], ckey)] = {
            "invoice_period": inv["invoice_period"],
            "customer_key": ckey,
            "invoiced_amount": inv.get("total_amount"),
            "paid_amount": inv.get("paid_amount"),
            "payment_status": inv.get("payment_status"),
            "days_late": inv.get("days_late"),
            "batch_id": batch_id,
        }

    fact_records = list(fact_rows.values())
    if not fact_records:
        return 0

    # PostgreSQL Idempotent Upsert
    stmt = pg_insert(FactBillingMonthly).values(fact_records)
    upsert_stmt = stmt.on_conflict_do_update(
        index_elements=["invoice_period", "customer_key"],
        set_={
            "invoiced_amount": stmt.excluded.invoiced_amount,
            "paid_amount": stmt.excluded.paid_amount,
            "payment_status": stmt.excluded.payment_status,
            "days_late": stmt.excluded.days_late,
            "batch_id": stmt.excluded.batch_id,
        },
    )

    await session.execute(upsert_stmt)
    await session.commit()
    logger.info(f"Loaded {len(fact_rows)} facts into feature_store.fact_billing_monthly")
    return len(fact_rows)
