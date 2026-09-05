from datetime import datetime, timezone
import logging
from typing import Any, Dict, List
import uuid
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import to_naive_utc, utc_now
from app.models.staging import (
    StgCustomerSubscription,
    StgSalesInvoice,
    StgSalesPayment,
)

logger = logging.getLogger("erp_ingestion.transformers.staging")


async def load_staging_subscriptions(
    session: AsyncSession, records: List[Dict[str, Any]], batch_id: uuid.UUID
) -> int:
    """Load raw extracted subscription records 1:1 into staging layer."""
    if not records:
        return 0

    stg_objects = []
    for r in records:
        stg_obj = StgCustomerSubscription(
            source_id=r["source_id"],
            customer_id=r.get("customer_id"),
            package_id=r.get("package_id"),
            subscription_no=r.get("subscription_no"),
            start_date=r.get("start_date"),
            end_date=r.get("end_date"),
            monthly_fee=r.get("monthly_fee"),
            billing_day=r.get("billing_day"),
            status=r.get("status"),
            source_updated_at=to_naive_utc(r.get("source_updated_at")),
            batch_id=batch_id,
            loaded_at=utc_now(),
        )
        stg_objects.append(stg_obj)

    session.add_all(stg_objects)
    await session.commit()
    logger.info(f"Loaded {len(stg_objects)} records into staging.stg_customer_subscription")
    return len(stg_objects)


async def load_staging_billing(
    session: AsyncSession,
    invoices: List[Dict[str, Any]],
    payments: List[Dict[str, Any]],
    batch_id: uuid.UUID,
) -> int:
    """Load raw extracted invoices and payments into staging layer."""
    stg_invs = [
        StgSalesInvoice(
            source_id=inv["source_id"],
            customer_subscription_id=inv.get("customer_subscription_id"),
            invoice_number=inv.get("invoice_number"),
            invoice_period=inv.get("invoice_period"),
            invoice_date=inv.get("invoice_date"),
            due_date=inv.get("due_date"),
            total_amount=inv.get("total_amount"),
            payment_status=inv.get("payment_status"),
            source_updated_at=to_naive_utc(inv.get("source_updated_at")),
            batch_id=batch_id,
            loaded_at=utc_now(),
        )
        for inv in invoices
    ]
    stg_pays = [
        StgSalesPayment(
            source_id=pay["source_id"],
            sales_invoice_id=pay.get("sales_invoice_id"),
            payment_date=pay.get("payment_date"),
            amount=pay.get("amount"),
            payment_status=pay.get("payment_status"),
            source_created_at=to_naive_utc(pay.get("source_created_at")),
            batch_id=batch_id,
            loaded_at=utc_now(),
        )
        for pay in payments
    ]

    session.add_all(stg_invs)
    session.add_all(stg_pays)
    await session.commit()
    logger.info(
        f"Loaded {len(stg_invs)} invoices and {len(stg_pays)} payments into staging."
    )
    return len(stg_invs) + len(stg_pays)
