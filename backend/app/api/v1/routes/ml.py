from datetime import date
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import EntityNotFoundError
from app.core.session import get_db
from app.ml.inference.churn_predictor import ChurnInferenceService
from app.ml.registry import (
    get_active_model_metadata,
    list_available_models,
    reload_active_model,
)
from app.ml.training.train_churn import train_customer_churn_model
from app.schemas.envelope import ResponseEnvelope, success_response
from app.schemas.ml import (
    BatchPredictionRequest,
    BatchPredictionResponse,
    CustomerRiskProfile,
    ModelMetadataResponse,
    ModelTrainRequest,
    ModelTrainResponse,
)

logger = logging.getLogger("erp_api.ml")
router = APIRouter(prefix="/ml", tags=["Machine Learning & Predictive Intelligence"])


@router.post(
    "/models/churn/train",
    response_model=ResponseEnvelope[ModelTrainResponse],
    status_code=status.HTTP_200_OK,
    summary="Train or Retrain Customer Churn Model (XGBoost)",
    description=(
        "Memicu siklus pelatihan model Customer Churn berbasis XGBoost. "
        "Mengambil data dari feature_store.feature_customer_churn, "
        "menerapkan anti-leakage temporal split, menghitung metrik evaluasi (ROC-AUC, F1, PR-AUC), "
        "menyimpan artifact terversi ke local registry, dan memperbarui pointer active_model.json."
    ),
)
async def train_churn_model_endpoint(
    request: Request,
    payload: Optional[ModelTrainRequest] = None,
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    req = payload or ModelTrainRequest()

    try:
        train_result = await train_customer_churn_model(
            session=session,
            model_version=req.model_version,
            hyperparameters=req.hyperparameters,
            test_size_ratio=req.test_size_ratio,
            set_as_active=req.set_as_active,
        )
        if req.set_as_active:
            reload_active_model()

        typed_resp = ModelTrainResponse(**train_result)
        return success_response(data=typed_resp.model_dump(), request_id=request_id)
    except Exception as e:
        logger.error(f"Training churn model failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal melatih model Customer Churn: {str(e)}",
        )


@router.get(
    "/models/churn/metadata",
    response_model=ResponseEnvelope[ModelMetadataResponse],
    summary="Get Currently Active Churn Model Metadata",
    description="Mengambil informasi versi model yang sedang aktif, tanggal pelatihan, daftar fitur, dan metrik akurasi.",
)
async def get_churn_metadata_endpoint(request: Request):
    request_id = getattr(request.state, "request_id", None)
    meta = get_active_model_metadata()

    if not meta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Belum ada model Churn aktif yang dilatih. Jalankan POST /api/v1/ml/models/churn/train terlebih dahulu.",
        )

    typed_resp = ModelMetadataResponse(
        model_name=meta.get("model_name", "churn_xgboost"),
        model_version=meta.get("model_version", "1.0.0"),
        algorithm=meta.get("algorithm", "XGBClassifier"),
        trained_at=meta.get("trained_at"),
        features=meta.get("features", []),
        metrics=meta.get("metrics"),
        is_active=True,
    )
    return success_response(data=typed_resp.model_dump(), request_id=request_id)


@router.get(
    "/models/churn/history",
    response_model=ResponseEnvelope[List[Dict[str, Any]]],
    summary="List All Available Churn Model Releases",
    description="Melihat riwayat seluruh versi model yang pernah dilatih di registry lokal.",
)
async def list_churn_models_endpoint(request: Request):
    request_id = getattr(request.state, "request_id", None)
    models = list_available_models()
    return success_response(data=models, request_id=request_id)


@router.post(
    "/predictions/churn/batch",
    response_model=ResponseEnvelope[BatchPredictionResponse],
    status_code=status.HTTP_200_OK,
    summary="Execute Batch Churn Prediction for a Snapshot",
    description=(
        "Menjalankan inferensi batch untuk semua pelanggan pada snapshot tertentu. "
        "Menghasilkan probabilitas, risk level (LOW/MED/HIGH), risk rank, dan top 3 driver risiko. "
        "Hasil disimpan secara idempotent (ON CONFLICT DO UPDATE) di feature_store.prediction_customer_churn."
    ),
)
async def predict_churn_batch_endpoint(
    request: Request,
    payload: Optional[BatchPredictionRequest] = None,
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    req = payload or BatchPredictionRequest()

    target_date = None
    if req.snapshot_date:
        try:
            target_date = date.fromisoformat(req.snapshot_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format snapshot_date harus YYYY-MM-DD",
            )

    try:
        batch_result = await ChurnInferenceService.predict_batch(
            session=session,
            snapshot_date=target_date,
            force_refresh=req.force_refresh,
        )
        typed_resp = BatchPredictionResponse(**batch_result)
        return success_response(data=typed_resp.model_dump(), request_id=request_id)
    except FileNotFoundError as fnf:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(fnf),
        )
    except Exception as e:
        logger.error(f"Batch churn prediction failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Inferensi batch gagal: {str(e)}",
        )


@router.get(
    "/predictions/churn/high-risk",
    response_model=ResponseEnvelope[List[CustomerRiskProfile]],
    summary="Get Top High-Risk Customers for Retention Focus",
    description=(
        "Mengembalikan daftar pelanggan berisiko tinggi terurut berdasarkan probabilitas churn tertinggi. "
        "Menyertakan nama pelanggan, kota, status, serta Top 3 faktor pemicu risiko (SHAP drivers)."
    ),
)
async def get_high_risk_customers_endpoint(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100, description="Maksimum jumlah pelanggan yang ditampilkan"),
    min_probability: float = Query(default=0.70, ge=0.0, le=1.0, description="Ambang batas probabilitas minimal"),
    snapshot_date: Optional[str] = Query(default=None, description="Tanggal snapshot (opsional, default: terbaru)"),
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    target_date = None
    if snapshot_date:
        try:
            target_date = date.fromisoformat(snapshot_date)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Format snapshot_date harus YYYY-MM-DD",
            )

    try:
        customers = await ChurnInferenceService.get_high_risk_customers(
            session=session,
            limit=limit,
            min_probability=min_probability,
            snapshot_date=target_date,
        )
        typed_data = [CustomerRiskProfile(**c).model_dump() for c in customers]
        return success_response(data=typed_data, request_id=request_id)
    except Exception as e:
        logger.error(f"Failed to retrieve high-risk customers: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengambil daftar pelanggan risiko tinggi: {str(e)}",
        )


@router.get(
    "/predictions/churn/customer/{customer_id}",
    response_model=ResponseEnvelope[CustomerRiskProfile],
    summary="Get Individual Customer Churn Risk Profile",
    description="Mengambil profil risiko churn dan detail driver pemicu untuk satu pelanggan tertentu.",
)
async def get_customer_prediction_endpoint(
    customer_id: int,
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    request_id = getattr(request.state, "request_id", None)
    customer_profile = await ChurnInferenceService.get_customer_prediction(
        session=session,
        customer_id=customer_id,
    )

    if not customer_profile:
        raise EntityNotFoundError(
            entity_name="PredictionCustomerChurn",
            entity_id=customer_id,
        )

    typed_data = CustomerRiskProfile(**customer_profile).model_dump()
    return success_response(data=typed_data, request_id=request_id)
