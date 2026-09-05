from datetime import datetime, timezone
import time
from fastapi import APIRouter, Request, status
from sqlalchemy import text

from app.core.config import settings
from app.core.session import engine
from app.schemas.envelope import ResponseEnvelope, success_response
from app.schemas.health import (
    DatabaseComponentHealth,
    FeatureStoreComponentHealth,
    HealthComponents,
    HealthResponse,
)

router = APIRouter()


@router.get(
    "/health",
    response_model=ResponseEnvelope[HealthResponse],
    status_code=status.HTTP_200_OK,
    summary="Health & System Readiness Check",
    description="Endpoint publik untuk memantau liveness dan readiness backend serta koneksi Feature Store.",
)
async def health_check(request: Request):
    request_id = getattr(request.state, "request_id", None)

    # Check database connectivity & latency
    db_status = "disconnected"
    latency_ms = None
    start_time = time.perf_counter()

    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            latency_ms = round((time.perf_counter() - start_time) * 1000, 2)
            db_status = "connected"
    except Exception:
        db_status = "disconnected"

    system_status = "healthy" if db_status == "connected" else "degraded"

    health_data = HealthResponse(
        status=system_status,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="0.1.0",
        environment=settings.ENVIRONMENT,
        components=HealthComponents(
            database=DatabaseComponentHealth(
                status=db_status,
                latency_ms=latency_ms,
                pool_size=settings.DB_POOL_SIZE,
                active_connections=1 if db_status == "connected" else 0,
            ),
            feature_store=FeatureStoreComponentHealth(
                status="ready" if db_status == "connected" else "uninitialized",
                schemas=["staging", "feature_store"],
            ),
        ),
    )

    return success_response(data=health_data.model_dump(), request_id=request_id)
