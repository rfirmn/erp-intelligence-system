import logging
from typing import Any, Dict, List
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import AppException
from app.schemas.envelope import error_response

logger = logging.getLogger("erp_api")


def register_exception_handlers(app: FastAPI) -> None:
    """Register uniform exception handlers mapping all errors to Universal Response Envelope."""

    @app.exception_handler(AppException)
    async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=exc.code,
                message=exc.message,
                details=exc.details,
                request_id=request_id,
            ),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        details: List[Dict[str, Any]] = []
        for error in exc.errors():
            loc = error.get("loc", [])
            # Skip 'body' or 'query' prefix if present for cleaner field name
            field_path = ".".join(str(x) for x in loc if x not in ("body", "query", "path"))
            if not field_path and loc:
                field_path = str(loc[-1])
            details.append({
                "field": field_path or "payload",
                "issue": error.get("msg", "Format data tidak sesuai."),
            })

        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=error_response(
                code="VALIDATION_ERROR",
                message="Payload request tidak memenuhi kriteria validasi.",
                details=details,
                request_id=request_id,
            ),
        )

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        code_map = {
            400: "BAD_REQUEST",
            401: "UNAUTHORIZED",
            403: "FORBIDDEN",
            404: "NOT_FOUND",
            409: "CONFLICT",
            422: "UNPROCESSABLE_ENTITY",
            500: "INTERNAL_SERVER_ERROR",
            503: "DATABASE_UNAVAILABLE",
        }
        code = code_map.get(exc.status_code, "BAD_REQUEST" if exc.status_code < 500 else "INTERNAL_SERVER_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=error_response(
                code=code,
                message=str(exc.detail),
                request_id=request_id,
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        request_id = getattr(request.state, "request_id", None)
        logger.error(f"Unhandled server error [request_id={request_id}]: {exc}", exc_info=True)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=error_response(
                code="INTERNAL_SERVER_ERROR",
                message="Terjadi kesalahan internal server yang tidak terduga.",
                details=[{"field": "server", "issue": str(exc)}] if app.debug else [],
                request_id=request_id,
            ),
        )
