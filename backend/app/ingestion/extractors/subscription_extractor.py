from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from app.core.datetime_utils import to_naive_utc
from app.ingestion.extractors.base import BaseExtractor
from app.ingestion.extractors.erp_client import erp_connector

logger = logging.getLogger("erp_ingestion.extractors.subscription")


class SubscriptionExtractor(BaseExtractor):
    """Extractor for ISP Customers, Packages, and Subscriptions."""

    def __init__(self):
        super().__init__(source_table="customer_subscription")

    async def extract(
        self,
        since: Optional[datetime],
        until: datetime,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        since = to_naive_utc(since)
        until = to_naive_utc(until) or datetime.utcnow()
        logger.info(
            f"Extracting subscriptions from {erp_connector.source_type} "
            f"with window=[{since} -> {until}]"
        )

        if erp_connector.is_mock:
            # Generate deterministic mock data
            mock_gen = erp_connector.get_mock_generator()
            return mock_gen.generate_subscriptions(since=since, until=until, count=120)

        # Live SQL query matching feature_store_schema_design.md
        query = """
            SELECT 
                cs.id AS source_id,
                cs.customer_id,
                c.customer_name AS customer_name,
                c.city,
                c.installation_date,
                cs.package_id,
                p.package_name,
                p.speed_mbps,
                cs.subscription_no,
                cs.start_date,
                cs.end_date,
                cs.monthly_fee,
                cs.billing_day,
                cs.status,
                cs.updated_at AS source_updated_at
            FROM customer_subscription cs
            LEFT JOIN customer c ON c.id = cs.customer_id
            LEFT JOIN internet_package p ON p.id = cs.package_id
            WHERE (CAST(:since AS TIMESTAMP) IS NULL OR cs.updated_at > CAST(:since AS TIMESTAMP))
              AND cs.updated_at <= :until
            ORDER BY cs.updated_at ASC
            LIMIT :limit;
        """
        params = {"since": since, "until": until, "limit": limit}
        rows = await erp_connector.execute_query(query, params)
        for r in rows:
            r["_is_mock"] = False
        return rows
