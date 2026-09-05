from datetime import datetime, timezone
import logging
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.core.config import settings
from app.core.session import get_db
from app.ingestion.extractors.erp_client import erp_connector
from app.ingestion.jobs.billing_sync import run_billing_sync
from app.ingestion.jobs.subscription_sync import run_subscription_sync
from app.ingestion.scheduler import list_scheduled_jobs
from app.models.metadata import DataQualityLog, ETLBatchLog
from app.schemas.envelope import ResponseEnvelope, success_response
from app.schemas.ingestion import (
    BatchLogItem,
    DataQualityLogItem,
    JobTriggerRequest,
    JobTriggerResponse,
    SchedulerJobItem,
)

logger = logging.getLogger("erp_api.ingestion")
router = APIRouter(prefix="/ingestion", tags=["Ingestion & Pipeline"])


@router.post(
    "/trigger/{job_name}",
    response_model=ResponseEnvelope[JobTriggerResponse],
    status_code=status.HTTP_200_OK,
    summary="Trigger Ingestion Batch Pipeline Manually",
    description=(
        "Memicu eksekusi sinkronisasi pipeline batch data ERP secara manual. "
        "Job yang tersedia: 'subscription_sync' dan 'billing_sync'. "
        "PERHATIAN: Jika sistem berjalan dalam fallback mode, data akan ditandai dengan 'is_mock_data: true'."
    ),
)
async def trigger_job(
    job_name: str,
    request: Request,
    response: Response,
    payload: Optional[JobTriggerRequest] = None,
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    req_data = payload or JobTriggerRequest()

    if job_name not in ["subscription_sync", "billing_sync"]:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Job '{job_name}' tidak ditemukan. Pilihan: ['subscription_sync', 'billing_sync']",
        )

    try:
        if job_name == "subscription_sync":
            result = await run_subscription_sync(
                session=session,
                limit=req_data.limit,
                force_full_refresh=req_data.force_full_refresh,
            )
        else:
            result = await run_billing_sync(
                session=session,
                limit=req_data.limit,
                force_full_refresh=req_data.force_full_refresh,
            )

        # Set safety headers and response
        if result["is_mock_data"]:
            response.headers["X-Data-Source"] = "MOCK_GENERATOR"
            response.headers["X-Mock-Warning"] = "DO_NOT_USE_IN_PRODUCTION"
        else:
            response.headers["X-Data-Source"] = "LIVE_ERP"

        typed_resp = JobTriggerResponse(**result)
        return success_response(data=typed_resp.model_dump(), request_id=request_id)

    except Exception as e:
        logger.error(f"Manual pipeline execution failed for '{job_name}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline execution failed: {str(e)}",
        )


@router.get(
    "/history",
    response_model=ResponseEnvelope[List[BatchLogItem]],
    summary="Get ETL Batch Execution Logs",
    description="Mengembalikan riwayat batch eksekusi ingestion pipeline dengan indikator mock/live yang jelas.",
)
async def get_history(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    query = (
        select(ETLBatchLog)
        .order_by(desc(col(ETLBatchLog.started_at)))
        .limit(limit)
    )
    res = await session.execute(query)
    logs = res.scalars().all()

    items = []
    for log in logs:
        is_mock = "[MOCK]" in (log.status or "")
        items.append(
            BatchLogItem(
                batch_id=str(log.batch_id),
                source_table=log.source_table,
                watermark_start=log.watermark_start.isoformat() if log.watermark_start else None,
                watermark_end=log.watermark_end.isoformat() if log.watermark_end else None,
                status=log.status,
                is_mock_data=is_mock,
                row_count=log.row_count or 0,
                started_at=log.started_at.isoformat() if log.started_at else datetime.now(timezone.utc).isoformat(),
                finished_at=log.finished_at.isoformat() if log.finished_at else None,
            ).model_dump()
        )

    return success_response(data=items, request_id=request_id)


@router.get(
    "/quality-reports",
    response_model=ResponseEnvelope[List[DataQualityLogItem]],
    summary="Get Data Quality Audit Logs",
    description="Mengembalikan laporan audit pemeriksaan kualitas data (null checks, non-negative checks).",
)
async def get_quality_reports(
    request: Request,
    status_filter: Optional[str] = Query(default=None, alias="status"),
    table_name: Optional[str] = None,
    limit: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    query = select(DataQualityLog).order_by(desc(col(DataQualityLog.checked_at))).limit(limit)

    if status_filter:
        query = query.where(col(DataQualityLog.status) == status_filter.upper())
    if table_name:
        query = query.where(col(DataQualityLog.table_name) == table_name)

    res = await session.execute(query)
    logs = res.scalars().all()

    items = [
        DataQualityLogItem(
            log_id=log.id or 0,
            batch_id=str(log.batch_id) if log.batch_id else None,
            check_name=log.check_name,
            table_name=log.table_name,
            status=log.status,
            details=log.details,
            checked_at=log.checked_at.isoformat(),
        ).model_dump()
        for log in logs
    ]

    return success_response(data=items, request_id=request_id)


@router.get(
    "/schedules",
    response_model=ResponseEnvelope[List[SchedulerJobItem]],
    summary="List Ingestion Scheduler Jobs",
    description="Melihat status cron schedule otomatis ingestion di background server.",
)
async def get_scheduler_status(request: Request):
    request_id = getattr(request.state, "request_id", None)
    jobs = list_scheduled_jobs()
    return success_response(data=jobs, request_id=request_id)


@router.get(
    "/source-mode",
    summary="Check ERP Data Source Mode",
    description="Mengetahui apakah backend terhubung ke Live DB ERP atau menggunakan Fallback Mock Generator.",
)
async def get_source_mode(request: Request):
    request_id = getattr(request.state, "request_id", None)
    data = {
        "source_type": erp_connector.source_type,
        "is_mock_data": erp_connector.is_mock,
        "environment": settings.ENVIRONMENT,
        "scheduler_enabled": settings.SCHEDULER_ENABLED,
        "allow_mock_in_production": settings.ALLOW_MOCK_IN_PRODUCTION,
        "warning": (
            "ATTENTION: Current ERP data source is MOCK SYNTHETIC GENERATOR. "
            "Data is simulated and tagged for testing purposes."
            if erp_connector.is_mock
            else "CONNECTED TO LIVE ERP DATABASE."
        ),
    }
    return success_response(data=data, request_id=request_id)
