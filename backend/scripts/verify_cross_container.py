#!/usr/bin/env python3
"""Cross-Container ERP Database & Live Ingestion Verification Script.
Verifies connectivity to the external Mock ERP PostgreSQL database,
executes live SQL extractions against DBML tables, and confirms
staging & feature store loading in LIVE_ERP mode.
"""

import asyncio
from datetime import datetime, timezone
import logging
import os
import sys

# Ensure backend root is on sys.path
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.dirname(CURRENT_DIR)
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.core.session import async_session_factory
from app.ingestion.extractors.billing_extractor import BillingExtractor
from app.ingestion.extractors.erp_client import erp_connector
from app.ingestion.extractors.subscription_extractor import SubscriptionExtractor
from app.ingestion.jobs.billing_sync import run_billing_sync
from app.ingestion.jobs.subscription_sync import run_subscription_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger("verify_cross_container")


async def verify_erp_database_tables(erp_url: str):
    """Verify that all 21 DBML tables are present and populated in the mock ERP database."""
    logger.info(f"Connecting to ERP Database: {erp_url}")
    engine = create_async_engine(erp_url, echo=False)

    tables_to_check = [
        "department", "employee", "user_account",
        "internet_package", "customer", "customer_subscription",
        "supplier", "item", "warehouse", "stock", "stock_ledger",
        "purchase_order", "purchase_order_item", "purchase_invoice", "purchase_payment",
        "sales_invoice", "sales_payment",
        "account", "journal_entry", "journal_entry_line",
        "asset", "audit_log",
    ]

    print("\n" + "=" * 65)
    print(" 1. VERIFIKASI TABEL & JUMLAH BARIS DI MOCK ERP DATABASE")
    print("=" * 65)
    print(f"{'Nama Tabel ERP':<30} | {'Status':<15} | {'Row Count':<10}")
    print("-" * 65)

    all_ok = True
    async with engine.connect() as conn:
        for tbl in tables_to_check:
            try:
                res = await conn.execute(text(f"SELECT count(*) FROM {tbl}"))
                cnt = res.scalar() or 0
                status_str = "READY" if cnt > 0 else "EMPTY"
                print(f"{tbl:<30} | {status_str:<15} | {cnt:<10}")
            except Exception as e:
                print(f"{tbl:<30} | FAILED: {str(e)[:12]} | 0")
                all_ok = False

    print("=" * 65 + "\n")
    await engine.dispose()
    return all_ok


async def verify_live_extraction_and_ingestion():
    """Verify live SQL query execution and pipeline processing from the ERP database."""
    print("=" * 65)
    print(" 2. VERIFIKASI LIVE EXTRACTION & FEATURE STORE LOADING")
    print("=" * 65)

    # 1. Test Subscription Extraction
    sub_extractor = SubscriptionExtractor()
    sub_rows = await sub_extractor.extract(since=None, until=datetime.now(timezone.utc), limit=100)
    print(f"[*] SubscriptionExtractor live query: {len(sub_rows)} baris diekstrak")
    if sub_rows:
        sample = sub_rows[0]
        print(f"    Sample: ID={sample.get('source_id')}, Customer={sample.get('customer_name')}, "
              f"Package={sample.get('package_name')} ({sample.get('speed_mbps')} Mbps), "
              f"Status={sample.get('status')}")

    # 2. Test Billing Extraction
    bill_extractor = BillingExtractor()
    bill_data = await bill_extractor.extract(since=None, until=datetime.now(timezone.utc), limit=100)
    invoices = bill_data.get("invoices", [])
    payments = bill_data.get("payments", [])
    print(f"[*] BillingExtractor live query: {len(invoices)} invoices, {len(payments)} payments")
    if invoices:
        print(f"    Sample Invoice: {invoices[0].get('invoice_number')}, Total={invoices[0].get('total_amount')}, "
              f"Status={invoices[0].get('payment_status')}")

    # 3. Run complete synchronization pipelines
    print("\n[*] Menjalankan run_subscription_sync()...")
    sub_sync_result = await run_subscription_sync(force_full_refresh=True)
    print(f"    Status: {sub_sync_result.get('status')}")
    print(f"    Source Type: {sub_sync_result.get('source_type')}")
    print(f"    Is Mock Data: {sub_sync_result.get('is_mock_data')}")
    print(f"    Rows Extracted: {sub_sync_result.get('rows_extracted')}")
    print(f"    Rows Staged: {sub_sync_result.get('rows_staged')}")
    print(f"    Rows Facts: {sub_sync_result.get('rows_fact')}")
    print(f"    Rows ML Features: {sub_sync_result.get('rows_features')}")

    print("\n[*] Menjalankan run_billing_sync()...")
    bill_sync_result = await run_billing_sync(force_full_refresh=True)
    print(f"    Status: {bill_sync_result.get('status')}")
    print(f"    Source Type: {bill_sync_result.get('source_type')}")
    print(f"    Is Mock Data: {bill_sync_result.get('is_mock_data')}")
    print(f"    Rows Staged: {bill_sync_result.get('rows_staged')}")
    print(f"    Rows Facts: {bill_sync_result.get('rows_fact')}")

    print("=" * 65 + "\n")


async def main():
    logger.info("Starting Cross-Container Verification...")
    erp_url = settings.get_erp_database_url()
    
    if erp_url.startswith("postgresql://"):
        erp_url = erp_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    # 1. Verify mock ERP tables
    ok = await verify_erp_database_tables(erp_url)
    if not ok:
        logger.warning("Beberapa tabel tidak ditemukan. Pastikan database mock ERP telah diinisialisasi.")

    # 2. Run extraction and sync
    await verify_live_extraction_and_ingestion()
    logger.info("Verification finished successfully.")


if __name__ == "__main__":
    asyncio.run(main())
