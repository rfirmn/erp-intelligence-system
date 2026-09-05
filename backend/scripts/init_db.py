import asyncio
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
from sqlmodel import SQLModel

import app.models  # Ensures all SQLModel tables are registered in SQLModel.metadata
from app.core.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("init_db")


async def create_database_if_not_exists():
    """Connect to default 'postgres' database to create the target database if missing."""
    auth = settings.POSTGRES_USER
    if settings.POSTGRES_PASSWORD:
        auth += f":{settings.POSTGRES_PASSWORD}"

    admin_url = f"postgresql+asyncpg://{auth}@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/postgres"

    logger.info(f"Checking existence of database '{settings.POSTGRES_DB}'...")
    try:
        admin_engine = create_async_engine(admin_url, isolation_level="AUTOCOMMIT")
        async with admin_engine.connect() as conn:
            result = await conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :dbname"),
                {"dbname": settings.POSTGRES_DB},
            )
            exists = result.scalar() is not None
            if not exists:
                logger.info(f"Database '{settings.POSTGRES_DB}' not found. Creating...")
                await conn.execute(text(f'CREATE DATABASE "{settings.POSTGRES_DB}"'))
                logger.info(f"Database '{settings.POSTGRES_DB}' created successfully.")
            else:
                logger.info(f"Database '{settings.POSTGRES_DB}' already exists.")
        await admin_engine.dispose()
    except Exception as e:
        logger.warning(f"Could not check/create database via admin connection: {e}")
        logger.info("Proceeding with direct connection attempt...")


async def init_feature_store_schema():
    """Create schemas, pgvector extension, and SQLModel tables in Feature Store."""
    target_url = settings.get_database_url()
    logger.info(f"Connecting to target database: {settings.POSTGRES_DB} on {settings.POSTGRES_HOST}...")

    engine = create_async_engine(target_url, echo=False)

    # 1. Create schemas
    logger.info("Ensuring schemas 'staging' and 'feature_store' exist...")
    async with engine.begin() as conn:
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS staging;"))
        await conn.execute(text("CREATE SCHEMA IF NOT EXISTS feature_store;"))

    # 2. Try creating pgvector extension in an isolated transaction
    try:
        logger.info("Attempting to enable 'vector' extension...")
        async with engine.begin() as conn:
            await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
        logger.info("Extension 'vector' enabled successfully.")
    except Exception as ve:
        logger.info(f"Extension 'vector' not available on this host: {ve}. Skipping (will be used in Docker pgvector).")

    # 3. Tables via SQLModel metadata
    logger.info("Creating all SQLModel metadata tables in 'staging' and 'feature_store'...")
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)

    await engine.dispose()

    # 4. Seed default dashboard user
    from app.core.session import ensure_default_dashboard_user
    await ensure_default_dashboard_user()

    logger.info("Feature Store initialization completed successfully!")


async def main():
    logger.info("=== Starting Feature Store Database Initialization ===")
    await create_database_if_not_exists()
    await init_feature_store_schema()
    logger.info("=== All Done ===")


if __name__ == "__main__":
    asyncio.run(main())
