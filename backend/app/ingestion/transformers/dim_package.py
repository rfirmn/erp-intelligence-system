from datetime import date
import logging
from typing import Any, Dict, List
from sqlmodel import col, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.dimensions import DimPackage

logger = logging.getLogger("erp_ingestion.transformers.dim_package")


async def sync_dim_package(
    session: AsyncSession, records: List[Dict[str, Any]], snapshot_date: date
) -> int:
    """Upsert ISP package dimension."""
    if not records:
        return 0

    packages_by_id: Dict[int, Dict[str, Any]] = {}
    for r in records:
        pkg_id = r.get("package_id")
        if pkg_id and pkg_id not in packages_by_id:
            packages_by_id[pkg_id] = {
                "package_id": pkg_id,
                "package_name": r.get("package_name"),
                "speed_mbps": r.get("speed_mbps"),
                "monthly_price": r.get("monthly_fee"),
            }

    count = 0
    for pkg_id, pdata in packages_by_id.items():
        q = select(DimPackage).where(
            col(DimPackage.package_id) == pkg_id, col(DimPackage.is_current) == True
        )
        res = await session.execute(q)
        existing = res.scalar_one_or_none()

        if not existing:
            new_pkg = DimPackage(
                package_id=pkg_id,
                package_name=pdata["package_name"],
                speed_mbps=pdata["speed_mbps"],
                monthly_price=pdata["monthly_price"],
                valid_from=snapshot_date,
                valid_to=None,
                is_current=True,
            )
            session.add(new_pkg)
            count += 1
        else:
            if (
                existing.package_name != pdata["package_name"]
                or existing.speed_mbps != pdata["speed_mbps"]
                or existing.monthly_price != pdata["monthly_price"]
            ):
                existing.package_name = pdata["package_name"]
                existing.speed_mbps = pdata["speed_mbps"]
                existing.monthly_price = pdata["monthly_price"]
                count += 1

    await session.commit()
    return count
