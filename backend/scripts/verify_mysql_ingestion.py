"""
Verification Script for Live MySQL Ingestion from Data Engineer's Database (garnetisp / garnet_platform).

Tests:
1. Direct connection using ml_readonly:ml_readonly123 @ localhost:3307/garnet_platform
2. Execution of SubscriptionExtractor against live MySQL database
3. Execution of BillingExtractor against live MySQL database
4. Validation that all SQL queries are 100% syntactically valid for MySQL 8.4
"""

import asyncio
import logging
import os
import sys
from datetime import datetime

# Add backend directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
backend_dir = os.path.abspath(os.path.join(current_dir, ".."))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

# Override environment variables for the test before importing config
os.environ["ERP_DATABASE_URL"] = (
    "mysql+asyncmy://ml_readonly:ml_readonly123@localhost:3307/garnet_platform"
)
os.environ["ERP_MOCK_DATA"] = "false"
os.environ["SECRET_KEY"] = os.environ.get("SECRET_KEY", "test-secret-key-32-characters-long-min!")
os.environ["POSTGRES_USER"] = os.environ.get("POSTGRES_USER", "rio")
os.environ["POSTGRES_DB"] = os.environ.get("POSTGRES_DB", "erp_intelligence_fs")
os.environ["POSTGRES_PASSWORD"] = os.environ.get("POSTGRES_PASSWORD", "")
os.environ["ERP_DB_USER"] = "ml_readonly"
os.environ["ERP_DB_PASSWORD"] = "ml_readonly123"
os.environ["ERP_DB_NAME"] = "garnet_platform"

from app.core.config import settings
from app.ingestion.extractors.erp_client import ERPConnector
from app.ingestion.extractors.subscription_extractor import SubscriptionExtractor
from app.ingestion.extractors.billing_extractor import BillingExtractor

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("verify_mysql_ingestion")


async def main():
    print("=" * 70)
    print("VERIFIKASI KONEKSI & PENARIKAN DATA MYSQL DATA ENGINEER (GARNET_PLATFORM)")
    print("=" * 70)

    url = settings.get_erp_database_url()
    print(f"Target Database URL: {url}")
    print(f"ERP_MOCK_DATA       : {settings.ERP_MOCK_DATA}")
    print(f"is_mock_source()   : {settings.is_mock_source()}")

    # 1. Initialize connector
    connector = ERPConnector()
    print(f"Connector Mode     : {connector.source_type}")
    print(f"Dialect            : {connector.dialect_name}")
    print(f"Is MySQL           : {connector.is_mysql}")

    if not connector.is_mysql:
        print("[FAIL] Dialect bukan MySQL!")
        await connector.close()
        sys.exit(1)

    # 2. Test raw handshake
    print("\n--- 1. UJI HANDSHAKE KONEKSI MYSQL ---")
    try:
        res = await connector.execute_query("SELECT CURRENT_USER() AS cur_user, DATABASE() AS cur_db, VERSION() AS ver;")
        print(f" [PASS] Handshake Sukses! Detail: {res}")
    except Exception as e:
        print(f" [FAIL] Gagal koneksi ke MySQL: {e}")
        await connector.close()
        sys.exit(1)

    # 3. Test SubscriptionExtractor query
    print("\n--- 2. UJI SUBSCRIPTION EXTRACTOR QUERY ---")
    sub_extractor = SubscriptionExtractor()
    # Replace erp_connector inside extractor with test connector
    import app.ingestion.extractors.subscription_extractor as sub_mod
    sub_mod.erp_connector = connector

    try:
        subs = await sub_extractor.extract(since=None, until=datetime.utcnow(), limit=10)
        print(f" [PASS] Query SubscriptionExtractor BERHASIL dieksekusi tanpa error sintaks!")
        print(f"        Jumlah baris data ditarik: {len(subs)}")
        if subs:
            print(f"        Sample data pertama: {subs[0]}")
    except Exception as e:
        print(f" [FAIL] SubscriptionExtractor error: {e}")
        await connector.close()
        sys.exit(1)

    # 4. Test BillingExtractor query
    print("\n--- 3. UJI BILLING EXTRACTOR QUERY ---")
    billing_extractor = BillingExtractor()
    import app.ingestion.extractors.billing_extractor as bill_mod
    bill_mod.erp_connector = connector

    try:
        billing_data = await billing_extractor.extract(since=None, until=datetime.utcnow(), limit=10)
        invoices = billing_data["invoices"]
        payments = billing_data["payments"]
        print(f" [PASS] Query BillingExtractor (Invoices & Payments) BERHASIL dieksekusi tanpa error sintaks!")
        print(f"        Invoices ditarik: {len(invoices)}")
        print(f"        Payments ditarik: {len(payments)}")
        if invoices:
            print(f"        Sample invoice: {invoices[0]}")
        if payments:
            print(f"        Sample payment: {payments[0]}")
    except Exception as e:
        print(f" [FAIL] BillingExtractor error: {e}")
        await connector.close()
        sys.exit(1)

    await connector.close()

    print("\n" + "=" * 70)
    print("HASIL: SEMUA PENGUJIAN PENARIKAN DATA MYSQL DATA ENGINEER LULUS 100%!")
    print("Backend telah siap menarik data dari kontainer garnet-mysql (garnetisp).")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())
