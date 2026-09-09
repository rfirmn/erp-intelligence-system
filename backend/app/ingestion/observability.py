from datetime import datetime, timezone
import logging
from typing import Optional
import uuid
from sqlalchemy import desc, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from sqlmodel import col
from app.core.datetime_utils import to_naive_utc, utc_now
from app.models.metadata import DataQualityLog, ETLBatchLog

logger = logging.getLogger("erp_ingestion.observability")


async def get_last_successful_watermark(
    session: AsyncSession, source_table: str
) -> Optional[datetime]:
    """Retrieve the latest successful watermark_end for an incremental table."""
    query = (
        select(col(ETLBatchLog.watermark_end))
        .where(
            col(ETLBatchLog.source_table) == source_table,
            col(ETLBatchLog.status).like("SUCCESS%"),
        )
        .order_by(desc(col(ETLBatchLog.finished_at)))
        .limit(1)
    )
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def start_batch(
    session: AsyncSession,
    source_table: str,
    watermark_start: Optional[datetime],
    watermark_end: Optional[datetime],
    is_mock: bool = False,
) -> uuid.UUID:
    """Create a new batch execution entry in etl_batch_log."""
    batch_id = uuid.uuid4()
    mock_marker = " [MOCK]" if is_mock else " [LIVE]"
    status_label = f"RUNNING{mock_marker}"

    batch_log = ETLBatchLog(
        batch_id=batch_id,
        source_table=source_table,
        watermark_start=to_naive_utc(watermark_start),
        watermark_end=to_naive_utc(watermark_end),
        status=status_label,
        started_at=utc_now(),
    )
    session.add(batch_log)
    await session.commit()
    logger.info(
        f"Batch started: id={batch_id}, source={source_table}, "
        f"window=[{watermark_start} -> {watermark_end}], is_mock={is_mock}"
    )
    return batch_id


async def finish_batch(
    session: AsyncSession,
    batch_id: uuid.UUID,
    row_count: int,
    status: str = "SUCCESS",
    is_mock: bool = False,
) -> None:
    """Mark batch execution complete with final status and row count."""
    mock_marker = " [MOCK]" if is_mock else " [LIVE]"
    status_label = f"{status}{mock_marker}"[:50]

    stmt = (
        update(ETLBatchLog)
        .where(col(ETLBatchLog.batch_id) == batch_id)
        .values(
            status=status_label,
            row_count=row_count,
            finished_at=utc_now(),
        )
    )
    await session.execute(stmt)
    await session.commit()
    logger.info(f"Batch finished: id={batch_id}, status={status_label}, row_count={row_count}")


async def record_data_quality(
    session: AsyncSession,
    check_name: str,
    table_name: str,
    status: str,  # PASS / FAIL / WARN
    details: Optional[str] = None,
    batch_id: Optional[uuid.UUID] = None,
) -> None:
    """Record an audit entry into data_quality_log."""
    dq_entry = DataQualityLog(
        batch_id=batch_id,
        check_name=check_name,
        table_name=table_name,
        status=status,
        details=details,
        checked_at=utc_now(),
    )
    session.add(dq_entry)
    await session.commit()
    log_func = logger.info if status == "PASS" else logger.warning
    log_func(f"Data Quality [{status}]: {check_name} on {table_name} - {details or 'OK'}")
