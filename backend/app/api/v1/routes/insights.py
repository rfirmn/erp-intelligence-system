import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.session import get_db
from app.insights.compiler import InsightCompiler
from app.schemas.envelope import ResponseEnvelope, success_response
from app.schemas.insights import InsightPackage

logger = logging.getLogger("erp_api.insights")
router = APIRouter(tags=["Insights & Executive Dashboard"])

VALID_MODULES = [
    "overview",
    "commercial",
    "finance",
    "procurement",
    "inventory",
    "asset",
    "service",
]


@router.get(
    "/dashboard/overview",
    response_model=ResponseEnvelope[InsightPackage],
    summary="Get Executive Overview Dashboard Insights",
    description="Mengambil wawasan ringkasan eksekutif tingkat tinggi lintas modul bisnis ISP.",
)
async def get_dashboard_overview(
    request: Request,
    as_of_date: Optional[str] = Query(default=None, description="Tanggal snapshot (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    try:
        compiler = InsightCompiler(session=session)
        package = await compiler.compile_module_insight(domain="overview", as_of_date=as_of_date)
        return success_response(data=package.model_dump(), request_id=request_id)
    except Exception as e:
        logger.error(f"Failed to compile dashboard overview: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengompilasi wawasan dashboard overview: {str(e)}",
        )


@router.get(
    "/insights/{module}",
    response_model=ResponseEnvelope[InsightPackage],
    summary="Get Domain Module Insights Package",
    description=(
        "Mengambil paket wawasan terstruktur untuk modul bisnis tertentu. "
        "Mencakup ringkasan eksekutif kritis LLM, kartu KPI, narasi temuan berbasis alasan agen, "
        "dan spesifikasi grafik Vega-Lite v5 yang terikat pada data aktual."
    ),
)
async def get_module_insight(
    module: str,
    request: Request,
    as_of_date: Optional[str] = Query(default=None, description="Tanggal snapshot (YYYY-MM-DD)"),
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    norm_module = module.lower()

    if norm_module not in VALID_MODULES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Modul '{module}' tidak valid. Pilihan modul: {VALID_MODULES}",
        )

    try:
        compiler = InsightCompiler(session=session)
        package = await compiler.compile_module_insight(domain=norm_module, as_of_date=as_of_date)
        return success_response(data=package.model_dump(), request_id=request_id)
    except Exception as e:
        logger.error(f"Failed to compile insight for module '{module}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengompilasi wawasan modul '{module}': {str(e)}",
        )
