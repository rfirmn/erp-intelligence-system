from fastapi import APIRouter
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.ingestion import router as ingestion_router
from app.api.v1.routes.insights import router as insights_router
from app.api.v1.routes.insights_mock import router as insights_mock_router
from app.api.v1.routes.ml import router as ml_router

api_v1_router = APIRouter()

api_v1_router.include_router(health_router, tags=["Health"])
api_v1_router.include_router(ingestion_router)
api_v1_router.include_router(auth_router)
api_v1_router.include_router(ml_router)
api_v1_router.include_router(insights_router)
api_v1_router.include_router(insights_mock_router)

__all__ = ["api_v1_router"]
