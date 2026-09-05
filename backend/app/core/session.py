from typing import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from app.core.config import settings

logger = logging.getLogger("erp_api.db")

engine: AsyncEngine = create_async_engine(
    settings.get_database_url(),
    echo=False,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_TIMEOUT_SECONDS,
)

async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that provides an asynchronous database session."""
    async with async_session_factory() as session:
        try:
            yield session
        finally:
            await session.close()


async def check_database_connection() -> bool:
    """Utility to quickly verify whether the database is accessible."""
    try:
        from sqlalchemy import text
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return True
    except Exception as e:
        logger.warning(f"Database connectivity check failed: {e}")
        return False
