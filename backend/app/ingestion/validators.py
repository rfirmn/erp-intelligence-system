import logging
from typing import Any, Dict, List, Optional
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from app.ingestion.observability import record_data_quality

logger = logging.getLogger("erp_ingestion.validators")


async def validate_not_null(
    session: AsyncSession,
    records: List[Dict[str, Any]],
    required_fields: List[str],
    table_name: str,
    batch_id: Optional[uuid.UUID] = None,
) -> bool:
    """Validate that required fields do not contain None or empty values."""
    if not records:
        await record_data_quality(
            session=session,
            check_name="null_check_empty_payload",
            table_name=table_name,
            status="WARN",
            details="No records received for validation.",
            batch_id=batch_id,
        )
        return True

    violations = 0
    for idx, row in enumerate(records):
        for field in required_fields:
            if row.get(field) is None:
                violations += 1
                if violations <= 5:  # Log first few violations only
                    logger.warning(f"Null violation on {table_name}.{field} at index {idx}")

    status = "PASS" if violations == 0 else "FAIL"
    details = f"Verified {len(records)} rows. Violations: {violations} null fields."
    await record_data_quality(
        session=session,
        check_name=f"null_check_{'_'.join(required_fields)}",
        table_name=table_name,
        status=status,
        details=details,
        batch_id=batch_id,
    )
    return violations == 0


async def validate_numeric_non_negative(
    session: AsyncSession,
    records: List[Dict[str, Any]],
    numeric_fields: List[str],
    table_name: str,
    batch_id: Optional[uuid.UUID] = None,
) -> bool:
    """Validate that financial and quantity numbers are non-negative."""
    violations = 0
    for row in records:
        for field in numeric_fields:
            val = row.get(field)
            if val is not None and isinstance(val, (int, float)) and val < 0:
                violations += 1

    status = "PASS" if violations == 0 else "FAIL"
    details = f"Verified {len(records)} rows for non-negative {numeric_fields}. Negative values: {violations}."
    await record_data_quality(
        session=session,
        check_name=f"non_negative_check_{'_'.join(numeric_fields)}",
        table_name=table_name,
        status=status,
        details=details,
        batch_id=batch_id,
    )
    return violations == 0
