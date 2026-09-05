from contextlib import asynccontextmanager
import logging
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.api.v1 import api_v1_router
from app.core.config import settings
from sqlmodel import SQLModel
import app.models  # Register all models in metadata
from app.core.handlers import register_exception_handlers
from app.core.session import check_database_connection, engine, ensure_default_dashboard_user
from app.ingestion.extractors.erp_client import erp_connector
from app.ingestion.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
)
logger = logging.getLogger("erp_api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup lifecycle
    logger.info(f"Starting {settings.PROJECT_NAME} in '{settings.ENVIRONMENT}' environment")
    logger.info(f"Security enabled: {settings.SECURITY_ENABLED}")
    logger.info(f"Allowed CORS origins: {settings.CORS_ORIGINS}")

    # Check database readiness
    is_db_connected = await check_database_connection()
    if is_db_connected:
        logger.info("Connected to PostgreSQL Feature Store database successfully.")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(SQLModel.metadata.create_all)
            await ensure_default_dashboard_user()
        except Exception as e:
            logger.warning(f"Could not auto-create tables or seed user: {e}")
    else:
        logger.warning(
            "Feature Store database is not reachable at startup. System starting in DEGRADED mode."
        )

    # Start APScheduler background ingestion tasks
    start_scheduler()

    yield

    # Shutdown lifecycle
    logger.info("Shutting down ERP Intelligence API backend...")
    stop_scheduler()
    await erp_connector.close()
    await engine.dispose()
    logger.info("Database connection pool and background scheduler closed.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version="0.1.0",
        description=(
            "Backend API untuk ERP Intelligence Dashboard ISP. "
            "Menyajikan wawasan analitis, model prediksi, dan data terstruktur Feature Store."
        ),
        openapi_url="/api/v1/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # 1. Request ID Middleware
    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    # 2. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID"],
    )

    # 3. Universal Error Handlers
    register_exception_handlers(app)

    # 4. API Routers
    app.include_router(api_v1_router, prefix=settings.API_V1_STR)

    # 5. Root documentation redirect
    @app.get("/", include_in_schema=False)
    async def root():
        return RedirectResponse(url="/docs")

    return app


app = create_app()
