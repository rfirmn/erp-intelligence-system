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


async def ensure_default_dashboard_user() -> None:
    """Ensure a default dashboard user account exists in feature_store.dim_user."""
    try:
        from sqlmodel import SQLModel, col, select
        import app.models  # Register all models in metadata
        from app.models.users import DimUser
        from app.core.security import get_password_hash

        # 1. Ensure table exists in database
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        # 2. Check and seed default user
        async with async_session_factory() as session:
            stmt = select(DimUser).where(col(DimUser.username) == settings.DEV_USER_USERNAME)
            res = await session.execute(stmt)
            existing_user = res.scalars().first()

            if not existing_user:
                logger.info(f"Seeding default dashboard user '{settings.DEV_USER_USERNAME}'...")
                default_user = DimUser(
                    username=settings.DEV_USER_USERNAME,
                    email=settings.DEV_USER_USERNAME,
                    hashed_password=get_password_hash(settings.DEV_USER_PASSWORD),
                    full_name=settings.DEV_USER_FULL_NAME,
                    is_active=True,
                )
                session.add(default_user)
                await session.commit()
                logger.info(f"Default dashboard user '{settings.DEV_USER_USERNAME}' created successfully.")
            else:
                logger.debug(f"Default dashboard user '{settings.DEV_USER_USERNAME}' already exists.")
    except Exception as e:
        logger.warning(f"Could not verify or seed default dashboard user: {e}")

