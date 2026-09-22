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

        # Check dialect
        if erp_connector.is_mysql:
            inv_where = ["(si.updated_at IS NULL OR si.updated_at <= :until)"]
            pay_where = ["(created_at IS NULL OR created_at <= :until)"]
            params: Dict[str, Any] = {"until": until, "limit": limit}
            if since is not None:
                inv_where.append("COALESCE(si.updated_at, si.created_at, si.invoice_date) > :since")
                pay_where.append("COALESCE(created_at, payment_date) > :since")
                params["since"] = since

            inv_where_sql = " AND ".join(inv_where)
            pay_where_sql = " AND ".join(pay_where)

            invoice_query = f"""
                SELECT 
                    si.id AS source_id,
                    si.customer_subscription_id,
                    cs.customer_id,
                    si.invoice_number,
                    si.invoice_period,
                    si.invoice_date,
                    si.due_date,
                    si.total_amount,
                    si.payment_status,
                    COALESCE(SUM(sp.amount_paid), 0.0) AS paid_amount,
                    CASE 
                        WHEN MAX(sp.payment_date) IS NOT NULL AND MAX(sp.payment_date) > si.due_date 
                            THEN DATEDIFF(MAX(sp.payment_date), si.due_date)
                        WHEN si.payment_status IN ('OVERDUE', 'UNPAID') AND CURRENT_DATE > si.due_date 
                            THEN DATEDIFF(CURRENT_DATE, si.due_date)
                        ELSE 0 
                    END AS days_late,
                    COALESCE(si.updated_at, si.created_at, CURRENT_TIMESTAMP) AS source_updated_at
                FROM sales_invoice si
                LEFT JOIN customer_subscription cs ON si.customer_subscription_id = cs.id
                LEFT JOIN sales_payment sp ON si.id = sp.sales_invoice_id AND sp.status = 'PAID'
                WHERE {inv_where_sql}
                GROUP BY si.id, cs.customer_id, si.customer_subscription_id, si.invoice_number,
                         si.invoice_period, si.invoice_date, si.due_date, si.total_amount,
                         si.payment_status, si.updated_at, si.created_at
                ORDER BY si.id ASC
                LIMIT :limit;
            """
            payment_query = f"""
                SELECT 
                    id AS source_id,
                    sales_invoice_id,
                    payment_date,
                    amount_paid AS amount,
                    status AS payment_status,
                    COALESCE(created_at, payment_date, CURRENT_TIMESTAMP) AS source_created_at
                FROM sales_payment
                WHERE {pay_where_sql}
                ORDER BY id ASC
                LIMIT :limit;
            """
        else:
            # PostgreSQL query
            inv_where = ["si.updated_at <= :until"]
            pay_where = ["created_at <= :until"]
            params = {"until": until, "limit": limit}
            if since is not None:
                inv_where.append("si.updated_at > :since")
                pay_where.append("created_at > :since")
                params["since"] = since

            inv_where_sql = " AND ".join(inv_where)
            pay_where_sql = " AND ".join(pay_where)

            invoice_query = f"""
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
                WHERE {inv_where_sql}
                GROUP BY si.id, cs.customer_id
                ORDER BY si.updated_at ASC
                LIMIT :limit;
            """
            payment_query = f"""
                SELECT 
                    id AS source_id,
                    sales_invoice_id,
                    payment_date,
                    amount,
                    payment_status,
                    created_at AS source_created_at
                FROM sales_payment
                WHERE {pay_where_sql}
                ORDER BY created_at ASC
                LIMIT :limit;
            """

        invoices = await erp_connector.execute_query(invoice_query, params)
        payments = await erp_connector.execute_query(payment_query, params)

        for inv in invoices:
            inv["_is_mock"] = False
            if "total_amount" in inv and inv["total_amount"] is not None:
                inv["total_amount"] = float(inv["total_amount"])
            if "paid_amount" in inv and inv["paid_amount"] is not None:
                inv["paid_amount"] = float(inv["paid_amount"])
            if "days_late" in inv and inv["days_late"] is not None:
                inv["days_late"] = int(inv["days_late"])
        for pay in payments:
            pay["_is_mock"] = False
            if "amount" in pay and pay["amount"] is not None:
                pay["amount"] = float(pay["amount"])

        return {"invoices": invoices, "payments": payments}
