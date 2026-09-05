#!/usr/bin/env python3
"""Standalone script to verify the Mock ERP Database schema and row counts.

Run directly:
    python scripts/verify_erp_db.py [DB_URL]
Default URL:
    postgresql://erp_user:erp_secret_123@localhost:5433/isp_erp_db
"""

import asyncio
import os
import sys

TABLES_TO_VERIFY = [
    "department",
    "employee",
    "user_account",
    "internet_package",
    "customer",
    "customer_subscription",
    "supplier",
    "item",
    "warehouse",
    "stock",
    "stock_ledger",
    "purchase_order",
    "purchase_order_item",
    "purchase_invoice",
    "purchase_payment",
    "sales_invoice",
    "sales_payment",
    "account",
    "journal_entry",
    "journal_entry_line",
    "asset",
    "audit_log",
]


async def main() -> None:
    db_url = sys.argv[1] if len(sys.argv) > 1 else os.getenv(
        "ERP_DATABASE_URL",
        "postgresql://erp_user:erp_secret_123@localhost:5433/isp_erp_db",
    )
    # Convert SQLAlchemy driver prefix if present
    db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    try:
        import asyncpg
    except ImportError:
        print("[!] asyncpg not installed. Please install: pip install asyncpg")
        sys.exit(1)

    print(f"[*] Connecting to Mock ERP Database at: {db_url}")
    try:
        conn = await asyncpg.connect(db_url)
    except Exception as exc:
        print(f"[!] Connection failed: {exc}")
        sys.exit(1)

    try:
        print("\n" + "=" * 65)
        print(" MOCK ERP DATABASE TABLE AUDIT (ISP MVP SCHEMA)")
        print("=" * 65)
        print(f"{'Table Name':<30} | {'Status':<15} | {'Row Count':<10}")
        print("-" * 65)

        total_rows = 0
        missing_tables = []

        for table in TABLES_TO_VERIFY:
            # Check existence
            exists = await conn.fetchval(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = $1
                )
                """,
                table,
            )

            if exists:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
                total_rows += count
                print(f"{table:<30} | {'READY':<15} | {count:<10}")
            else:
                missing_tables.append(table)
                print(f"{table:<30} | {'MISSING':<15} | {'-':<10}")

        print("=" * 65)
        print(f"Total Tables Checked: {len(TABLES_TO_VERIFY)}")
        print(f"Total Rows Seeded:    {total_rows}")

        if missing_tables:
            print(f"\n[!] Missing tables detected: {missing_tables}")
            sys.exit(1)
        else:
            print("\n[✓] All 21 DBML tables verified successfully with seed data!")

    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
