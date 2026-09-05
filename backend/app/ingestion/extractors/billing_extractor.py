from datetime import datetime
import logging
from typing import Any, Dict, List, Optional
from app.core.datetime_utils import to_naive_utc
from app.ingestion.extractors.base import BaseExtractor
from app.ingestion.extractors.erp_client import erp_connector

logger = logging.getLogger("erp_ingestion.extractors.billing")


class BillingExtractor(BaseExtractor):
    """Extractor for ISP Invoices and Payment transactions."""

    def __init__(self):
        super().__init__(source_table="sales_invoice")

    async def extract(
        self,
        since: Optional[datetime],
        until: datetime,
        limit: int = 5000,
        subscriptions_cache: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        since = to_naive_utc(since)
        until = to_naive_utc(until) or datetime.utcnow()
        logger.info(
            f"Extracting billing & payments from {erp_connector.source_type} "
            f"with window=[{since} -> {until}]"
        )

        if erp_connector.is_mock:
            mock_gen = erp_connector.get_mock_generator()
            subs = subscriptions_cache or mock_gen.generate_subscriptions()
            return mock_gen.generate_invoices_and_payments(subs, periods=3)

        # Live ERP queries for sales_invoice
        invoice_query = """
            SELECT 
                id AS source_id,
                customer_subscription_id,
                invoice_number,
                invoice_period,
                invoice_date,
                due_date,
                total_amount,
                payment_status,
                updated_at AS source_updated_at
            FROM sales_invoice
            WHERE (CAST(:since AS TIMESTAMP) IS NULL OR updated_at > CAST(:since AS TIMESTAMP))
              AND updated_at <= :until
            ORDER BY updated_at ASC
            LIMIT :limit;
        """
        payment_query = """
            SELECT 
                id AS source_id,
                sales_invoice_id,
                payment_date,
                amount,
                payment_status,
                created_at AS source_created_at
            FROM sales_payment
            WHERE (CAST(:since AS TIMESTAMP) IS NULL OR created_at > CAST(:since AS TIMESTAMP))
              AND created_at <= :until
            ORDER BY created_at ASC
            LIMIT :limit;
        """
        params = {"since": since, "until": until, "limit": limit}
        invoices = await erp_connector.execute_query(invoice_query, params)
        payments = await erp_connector.execute_query(payment_query, params)

        for inv in invoices:
            inv["_is_mock"] = False
        for pay in payments:
            pay["_is_mock"] = False

        return {"invoices": invoices, "payments": payments}
