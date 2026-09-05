from datetime import date, datetime, timedelta, timezone
import logging
import random
from typing import Any, Dict, List, Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import settings
from app.core.datetime_utils import to_naive_utc

logger = logging.getLogger("erp_ingestion.erp_client")


class MockERPGenerator:
    """Deterministic synthetic ISP ERP data generator for offline/dev testing.
    Emits data matching the schema of the external ISP ERP system.
    """

    PACKAGES = [
        {"id": 1, "package_name": "Home Starter 30 Mbps", "speed_mbps": 30, "monthly_price": 275000.0},
        {"id": 2, "package_name": "Home Fast 50 Mbps", "speed_mbps": 50, "monthly_price": 385000.0},
        {"id": 3, "package_name": "Home Ultra 100 Mbps", "speed_mbps": 100, "monthly_price": 550000.0},
        {"id": 4, "package_name": "Business Pro 200 Mbps", "speed_mbps": 200, "monthly_price": 1250000.0},
        {"id": 5, "package_name": "Dedicated Enterprise 500 Mbps", "speed_mbps": 500, "monthly_price": 4500000.0},
    ]

    CITIES = ["Jakarta Selatan", "Jakarta Barat", "Bandung", "Surabaya", "Tangerang", "Bekasi"]

    def __init__(self, seed: int = 42):
        self.rng = random.Random(seed)

    def generate_subscriptions(
        self, since: Optional[datetime] = None, until: Optional[datetime] = None, count: int = 120
    ) -> List[Dict[str, Any]]:
        since = to_naive_utc(since)
        until = to_naive_utc(until)
        records = []
        base_date = date(2025, 1, 1)

        for i in range(1, count + 1):
            pkg = self.rng.choice(self.PACKAGES)
            install_offset = self.rng.randint(0, 365)
            start_date = base_date + timedelta(days=install_offset)

            # Simulated status: 80% ACTIVE, 12% SUSPENDED (late pay), 8% TERMINATED
            r_val = self.rng.random()
            if r_val < 0.80:
                status = "ACTIVE"
            elif r_val < 0.92:
                status = "SUSPENDED"
            else:
                status = "TERMINATED"

            upd_time = datetime(2026, 8, 1, 10, 0, 0) + timedelta(hours=i * 2)

            if since and upd_time <= since:
                continue
            if until and upd_time > until:
                continue

            records.append({
                "source_id": i,
                "customer_id": 1000 + i,
                "customer_name": f"Pelanggan ISP #{i} [MOCK]",
                "city": self.rng.choice(self.CITIES),
                "installation_date": start_date,
                "package_id": pkg["id"],
                "package_name": pkg["package_name"],
                "speed_mbps": pkg["speed_mbps"],
                "subscription_no": f"SUB-ISP-{20260000 + i}",
                "start_date": start_date,
                "end_date": None,
                "monthly_fee": pkg["monthly_price"],
                "billing_day": (i % 28) + 1,
                "status": status,
                "source_updated_at": upd_time,
                "_is_mock": True,
            })
        return records

    def generate_invoices_and_payments(
        self, subscriptions: List[Dict[str, Any]], periods: int = 3
    ) -> Dict[str, List[Dict[str, Any]]]:
        invoices = []
        payments = []
        inv_id_counter = 1
        pay_id_counter = 1

        for sub in subscriptions:
            cust_id = sub["customer_id"]
            monthly_fee = sub["monthly_fee"]

            for p in range(periods):
                inv_period = date(2026, 6 + p, 1)
                inv_date = date(2026, 6 + p, sub["billing_day"])
                due_date = inv_date + timedelta(days=14)

                # Simulated behavior based on subscription status
                if sub["status"] == "TERMINATED" and p == periods - 1:
                    pay_status = "UNPAID"
                    days_late = 30
                    paid_amount = 0.0
                    pay_date = None
                elif sub["status"] == "SUSPENDED":
                    pay_status = "OVERDUE" if p == periods - 1 else "PAID"
                    days_late = 18 if p == periods - 1 else 5
                    paid_amount = monthly_fee if pay_status == "PAID" else 0.0
                    pay_date = due_date + timedelta(days=days_late) if pay_status == "PAID" else None
                else:
                    pay_status = "PAID"
                    days_late = self.rng.choice([0, 0, 0, 2, 5])
                    paid_amount = monthly_fee
                    pay_date = due_date + timedelta(days=days_late)

                upd_time = datetime(inv_date.year, inv_date.month, inv_date.day, 8, 0)

                invoices.append({
                    "source_id": inv_id_counter,
                    "customer_subscription_id": sub["source_id"],
                    "customer_id": cust_id,
                    "invoice_number": f"INV/{inv_period.strftime('%Y%m')}/{inv_id_counter:06d}",
                    "invoice_period": inv_period,
                    "invoice_date": inv_date,
                    "due_date": due_date,
                    "total_amount": monthly_fee,
                    "paid_amount": paid_amount,
                    "payment_status": pay_status,
                    "days_late": days_late,
                    "source_updated_at": upd_time,
                    "_is_mock": True,
                })

                if pay_date and paid_amount > 0:
                    payments.append({
                        "source_id": pay_id_counter,
                        "sales_invoice_id": inv_id_counter,
                        "payment_date": pay_date,
                        "amount": paid_amount,
                        "payment_status": "SUCCESS",
                        "source_created_at": datetime(pay_date.year, pay_date.month, pay_date.day, 12, 0),
                        "_is_mock": True,
                    })
                    pay_id_counter += 1

                inv_id_counter += 1

        return {"invoices": invoices, "payments": payments}


class ERPConnector:
    """Manages read-only connection to external ERP database or switches to mock data generator."""

    def __init__(self):
        self._engine: Optional[AsyncEngine] = None
        self._is_mock = settings.is_mock_source()
        self._mock_gen = MockERPGenerator()

        if not self._is_mock:
            url = settings.get_erp_database_url()
            if url:
                logger.info("Initializing live read-only connection to external ERP database...")
                if url.startswith("postgresql://"):
                    url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
                self._engine = create_async_engine(url, echo=False, pool_size=settings.ERP_DB_POOL_SIZE)
        else:
            logger.info("ERPConnector running in MOCK GENERATOR mode. Data will be tagged as mock.")

    @property
    def is_mock(self) -> bool:
        return self._is_mock

    @property
    def source_type(self) -> str:
        return "MOCK_GENERATOR" if self._is_mock else "LIVE_ERP"

    async def execute_query(self, query_str: str, params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Run SQL query against external ERP read-only database."""
        if self._is_mock or not self._engine:
            raise RuntimeError("Cannot execute live query in mock mode.")

        async with self._engine.connect() as conn:
            result = await conn.execute(text(query_str), params or {})
            columns = result.keys()
            rows = result.fetchall()
            return [{col: val for col, val in zip(columns, row)} for row in rows]

    def get_mock_generator(self) -> MockERPGenerator:
        return self._mock_gen

    async def close(self):
        if self._engine:
            await self._engine.dispose()


erp_connector = ERPConnector()
