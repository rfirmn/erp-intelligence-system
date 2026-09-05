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
                si.id AS source_id,
                si.customer_subscription_id,
                cs.customer_id,
                si.invoice_number,
                si.invoice_period,
                si.invoice_date,
                si.due_date,
                si.total_amount::float AS total_amount,
                si.payment_status,
                COALESCE(SUM(sp.amount), 0.0)::float AS paid_amount,
                CASE 
                    WHEN MAX(sp.payment_date) IS NOT NULL AND MAX(sp.payment_date) > si.due_date 
                        THEN (MAX(sp.payment_date) - si.due_date)::int
                    WHEN si.payment_status IN ('OVERDUE', 'UNPAID') AND CURRENT_DATE > si.due_date 
                        THEN (CURRENT_DATE - si.due_date)::int
                    ELSE 0 
                END AS days_late,
                si.updated_at AS source_updated_at
            FROM sales_invoice si
            LEFT JOIN customer_subscription cs ON si.customer_subscription_id = cs.id
            LEFT JOIN sales_payment sp ON si.id = sp.sales_invoice_id AND sp.payment_status = 'SUCCESS'
            WHERE (CAST(:since AS TIMESTAMP) IS NULL OR si.updated_at > CAST(:since AS TIMESTAMP))
              AND si.updated_at <= :until
            GROUP BY si.id, cs.customer_id
            ORDER BY si.updated_at ASC
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
