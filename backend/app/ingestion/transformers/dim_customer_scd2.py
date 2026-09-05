from datetime import date
import logging
from typing import Any, Dict, List
from sqlmodel import col, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.datetime_utils import to_naive_utc
from app.models.dimensions import DimCustomer

logger = logging.getLogger("erp_ingestion.transformers.scd2")


async def sync_dim_customer_scd2(
    session: AsyncSession, records: List[Dict[str, Any]], snapshot_date: date
) -> int:
    """Synchronize customer dimension using Slowly Changing Dimension (SCD) Type 2."""
    if not records:
        return 0

    # Group by customer_id to keep latest state in current batch
    latest_per_cust: Dict[int, Dict[str, Any]] = {}
    for r in records:
        cust_id = r.get("customer_id")
        if cust_id:
            latest_per_cust[cust_id] = r

    affected_count = 0

    for cust_id, r in latest_per_cust.items():
        # Query current active dimension record
        query = select(DimCustomer).where(
            col(DimCustomer.customer_id) == cust_id,
            col(DimCustomer.is_current) == True,
        )
        res = await session.execute(query)
        current_dim = res.scalar_one_or_none()

        new_name = r.get("customer_name")
        new_city = r.get("city")
        new_status = r.get("status")
        upd_at = to_naive_utc(r.get("source_updated_at"))
        install_date = r.get("installation_date") or snapshot_date

        if not current_dim:
            # First time seeing this customer: Insert version 1
            new_row = DimCustomer(
                customer_id=cust_id,
                customer_name=new_name,
                city=new_city,
                installation_date=install_date,
                status=new_status,
                valid_from=install_date,
                valid_to=None,
                is_current=True,
                source_updated_at=upd_at,
            )
            session.add(new_row)
            affected_count += 1
        else:
            # Check if attributes changed (SCD Type 2 trigger)
            has_changed = (
                current_dim.status != new_status
                or current_dim.city != new_city
                or current_dim.customer_name != new_name
            )

            if has_changed:
                # Close out previous version
                current_dim.valid_to = snapshot_date
                current_dim.is_current = False

                # Insert new active version
                new_version = DimCustomer(
                    customer_id=cust_id,
                    customer_name=new_name,
                    city=new_city,
                    installation_date=current_dim.installation_date,
                    status=new_status,
                    valid_from=snapshot_date,
                    valid_to=None,
                    is_current=True,
                    source_updated_at=upd_at,
                )
                session.add(new_version)
                affected_count += 1
            else:
                # Update watermark/updated_at timestamp without creating new version
                current_dim.source_updated_at = upd_at

    await session.commit()
    logger.info(f"SCD Type 2 sync completed: {affected_count} dimension rows created/updated.")
    return affected_count
