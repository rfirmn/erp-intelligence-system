from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import async_session_factory
from app.ingestion.extractors.billing_extractor import BillingExtractor
from app.ingestion.extractors.erp_client import erp_connector
from app.ingestion.observability import (
    finish_batch,
    get_last_successful_watermark,
    start_batch,
)
from app.ingestion.transformers.fact_billing_transformer import load_fact_billing_monthly
from app.ingestion.transformers.staging_loader import load_staging_billing
from app.ingestion.validators import (
    validate_not_null,
    validate_numeric_non_negative,
)

logger = logging.getLogger("erp_ingestion.jobs.billing")


async def run_billing_sync(
    session: Optional[AsyncSession] = None,
    limit: int = 5000,
    force_full_refresh: bool = False,
) -> Dict[str, Any]:
    """Execute complete ingestion pipeline for ISP Billing & Payments:
    Extractor -> Data Quality -> Staging -> Monthly Billing Facts.
    """
    if session is not None:
        return await _execute_billing_sync(session, limit, force_full_refresh)

    async with async_session_factory() as new_session:
        return await _execute_billing_sync(new_session, limit, force_full_refresh)


async def _execute_billing_sync(
    session: AsyncSession,
    limit: int = 5000,
    force_full_refresh: bool = False,
) -> Dict[str, Any]:
    is_mock = erp_connector.is_mock
    source_type = erp_connector.source_type
    watermark_end = datetime.now(timezone.utc)

    watermark_start = None
    if not force_full_refresh:
        watermark_start = await get_last_successful_watermark(
            session, "sales_invoice"
        )

    batch_id = await start_batch(
        session=session,
        source_table="sales_invoice",
        watermark_start=watermark_start,
        watermark_end=watermark_end,
        is_mock=is_mock,
    )

    try:
        # 1. Extraction from ERP (or Mock fallback)
        extractor = BillingExtractor()
        extracted_data = await extractor.extract(
            since=watermark_start, until=watermark_end, limit=limit
        )
        invoices = extracted_data.get("invoices", [])
        payments = extracted_data.get("payments", [])
        total_extracted = len(invoices) + len(payments)

        if not invoices and not payments:
            await finish_batch(
                session=session,
                batch_id=batch_id,
                row_count=0,
                status="SUCCESS",
                is_mock=is_mock,
            )
            return {
                "batch_id": str(batch_id),
                "job_name": "billing_sync",
                "is_mock_data": is_mock,
                "source_type": source_type,
                "status": "SUCCESS",
                "rows_extracted": 0,
                "rows_staged": 0,
                "rows_fact": 0,
                "invoices_count": 0,
                "payments_count": 0,
                "watermark_start": watermark_start.isoformat() if watermark_start else None,
                "watermark_end": watermark_end.isoformat(),
            }

        # 2. Data Quality Pre-Validation
        if invoices:
            await validate_not_null(
                session=session,
                records=invoices,
                required_fields=["source_id", "invoice_number", "customer_subscription_id"],
                table_name="stg_sales_invoice",
                batch_id=batch_id,
            )
            await validate_numeric_non_negative(
                session=session,
                records=invoices,
                numeric_fields=["total_amount", "paid_amount"],
                table_name="stg_sales_invoice",
                batch_id=batch_id,
            )

        if payments:
            await validate_not_null(
                session=session,
                records=payments,
                required_fields=["source_id", "sales_invoice_id"],
                table_name="stg_sales_payment",
                batch_id=batch_id,
            )
            await validate_numeric_non_negative(
                session=session,
                records=payments,
                numeric_fields=["amount"],
                table_name="stg_sales_payment",
                batch_id=batch_id,
            )

        # 3. Load into Staging Layer
        staged_count = await load_staging_billing(
            session=session, invoices=invoices, payments=payments, batch_id=batch_id
        )

        # 4. Load Monthly Fact Billing
        fact_count = await load_fact_billing_monthly(
            session=session, invoices=invoices, batch_id=batch_id
        )

        # 5. Complete Batch Logging
        await finish_batch(
            session=session,
            batch_id=batch_id,
            row_count=staged_count,
            status="SUCCESS",
            is_mock=is_mock,
        )

        return {
            "batch_id": str(batch_id),
            "job_name": "billing_sync",
            "is_mock_data": is_mock,
            "source_type": source_type,
            "status": "SUCCESS",
            "rows_extracted": total_extracted,
            "rows_staged": staged_count,
            "rows_fact": fact_count,
            "invoices_count": len(invoices),
            "payments_count": len(payments),
            "watermark_start": watermark_start.isoformat() if watermark_start else None,
            "watermark_end": watermark_end.isoformat(),
        }

    except Exception as e:
        logger.error(f"Billing sync failed: {e}", exc_info=True)
        await finish_batch(
            session=session,
            batch_id=batch_id,
            row_count=0,
            status=f"FAILED: {str(e)[:150]}",
            is_mock=is_mock,
        )
        raise
