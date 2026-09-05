from datetime import date, datetime, timezone
import logging
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import async_session_factory
from app.ingestion.extractors.erp_client import erp_connector
from app.ingestion.extractors.subscription_extractor import SubscriptionExtractor
from app.ingestion.observability import (
    finish_batch,
    get_last_successful_watermark,
    start_batch,
)
from app.ingestion.transformers.dim_customer_scd2 import sync_dim_customer_scd2
from app.ingestion.transformers.dim_package import sync_dim_package
from app.ingestion.transformers.fact_subscription_transformer import (
    load_fact_subscription_snapshot,
)
from app.ingestion.transformers.feature_churn_transformer import (
    build_feature_customer_churn,
)
from app.ingestion.transformers.staging_loader import load_staging_subscriptions
from app.ingestion.validators import (
    validate_not_null,
    validate_numeric_non_negative,
)

logger = logging.getLogger("erp_ingestion.jobs.subscription")


async def run_subscription_sync(
    session: Optional[AsyncSession] = None,
    limit: int = 5000,
    force_full_refresh: bool = False,
) -> Dict[str, Any]:
    """Execute complete ingestion pipeline for ISP Subscriptions:
    Extractor -> Data Quality -> Staging -> Dimensions (SCD2) -> Facts -> Feature Store.
    """
    if session is not None:
        return await _execute_subscription_sync(session, limit, force_full_refresh)

    async with async_session_factory() as new_session:
        return await _execute_subscription_sync(new_session, limit, force_full_refresh)


async def _execute_subscription_sync(
    session: AsyncSession,
    limit: int = 5000,
    force_full_refresh: bool = False,
) -> Dict[str, Any]:
    is_mock = erp_connector.is_mock
    source_type = erp_connector.source_type
    watermark_end = datetime.now(timezone.utc)
    snapshot_date = watermark_end.date()

    watermark_start = None
    if not force_full_refresh:
        watermark_start = await get_last_successful_watermark(
            session, "customer_subscription"
        )

    batch_id = await start_batch(
        session=session,
        source_table="customer_subscription",
        watermark_start=watermark_start,
        watermark_end=watermark_end,
        is_mock=is_mock,
    )

    try:
        # 1. Extraction from ERP (or Mock fallback)
        extractor = SubscriptionExtractor()
        records = await extractor.extract(
            since=watermark_start, until=watermark_end, limit=limit
        )

        if not records:
            await finish_batch(
                session=session,
                batch_id=batch_id,
                row_count=0,
                status="SUCCESS",
                is_mock=is_mock,
            )
            return {
                "batch_id": str(batch_id),
                "job_name": "subscription_sync",
                "is_mock_data": is_mock,
                "source_type": source_type,
                "status": "SUCCESS",
                "rows_extracted": 0,
                "rows_staged": 0,
                "rows_dimension": 0,
                "rows_fact": 0,
                "rows_features": 0,
                "watermark_start": watermark_start.isoformat() if watermark_start else None,
                "watermark_end": watermark_end.isoformat(),
            }

        # 2. Data Quality Pre-Validation
        await validate_not_null(
            session=session,
            records=records,
            required_fields=["source_id", "customer_id", "subscription_no"],
            table_name="stg_customer_subscription",
            batch_id=batch_id,
        )
        await validate_numeric_non_negative(
            session=session,
            records=records,
            numeric_fields=["monthly_fee"],
            table_name="stg_customer_subscription",
            batch_id=batch_id,
        )

        # 3. Load into Staging Layer
        staged_count = await load_staging_subscriptions(
            session=session, records=records, batch_id=batch_id
        )

        # 4. Synchronize Dimensions
        pkg_count = await sync_dim_package(
            session=session, records=records, snapshot_date=snapshot_date
        )
        cust_count = await sync_dim_customer_scd2(
            session=session, records=records, snapshot_date=snapshot_date
        )

        # 5. Load Periodic Snapshot Facts
        fact_count = await load_fact_subscription_snapshot(
            session=session,
            records=records,
            snapshot_date=snapshot_date,
            batch_id=batch_id,
        )

        # 6. Build Wide ML Features (Customer Churn)
        feat_count = await build_feature_customer_churn(
            session=session, snapshot_date=snapshot_date, batch_id=batch_id
        )

        # 7. Complete Batch Logging
        await finish_batch(
            session=session,
            batch_id=batch_id,
            row_count=staged_count,
            status="SUCCESS",
            is_mock=is_mock,
        )

        return {
            "batch_id": str(batch_id),
            "job_name": "subscription_sync",
            "is_mock_data": is_mock,
            "source_type": source_type,
            "status": "SUCCESS",
            "rows_extracted": len(records),
            "rows_staged": staged_count,
            "rows_dimension": cust_count + pkg_count,
            "rows_fact": fact_count,
            "rows_features": feat_count,
            "watermark_start": watermark_start.isoformat() if watermark_start else None,
            "watermark_end": watermark_end.isoformat(),
        }

    except Exception as e:
        logger.error(f"Subscription sync failed: {e}", exc_info=True)
        await finish_batch(
            session=session,
            batch_id=batch_id,
            row_count=0,
            status=f"FAILED: {str(e)[:150]}",
            is_mock=is_mock,
        )
        raise
