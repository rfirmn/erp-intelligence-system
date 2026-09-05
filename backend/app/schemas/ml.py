from datetime import date
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class ModelTrainRequest(BaseModel):
    model_version: str = Field(default="1.0.0", description="Versi model semantic yang akan dilatih")
    test_size_ratio: float = Field(
        default=0.2, ge=0.05, le=0.5, description="Proporsi data temporal untuk validasi OOT"
    )
    hyperparameters: Optional[Dict[str, Any]] = Field(
        default=None, description="Custom hyperparameter dictionary untuk XGBoost"
    )
    set_as_active: bool = Field(
        default=True, description="Jika true, langsung jadikan model ini sebagai active inference model"
    )


class ModelTrainResponse(BaseModel):
    model_name: str
    model_version: str
    status: str
    trained_at: str
    total_samples: int
    metrics: Dict[str, Any]
    top_global_features: List[Dict[str, Any]]
    is_active: bool


class ModelMetadataResponse(BaseModel):
    model_name: str
    model_version: str
    algorithm: Optional[str] = "XGBClassifier"
    trained_at: Optional[str] = None
    features: List[str] = []
    metrics: Optional[Dict[str, Any]] = None
    is_active: bool = True


class BatchPredictionRequest(BaseModel):
    snapshot_date: Optional[str] = Field(
        default=None,
        description="Tanggal snapshot fitur (YYYY-MM-DD). Jika null, otomatis gunakan snapshot terbaru.",
    )
    force_refresh: bool = Field(
        default=True, description="Jika true, lakukan overwrite idempotent pada prediksi yang sudah ada"
    )


class BatchPredictionResponse(BaseModel):
    snapshot_date: str
    model_version: str
    total_evaluated: int
    high_risk_count: int
    medium_risk_count: int
    low_risk_count: int
    average_churn_probability: float
    rows_saved: int


class CustomerRiskFactor(BaseModel):
    feature: str
    impact: str
    severity: Literal["LOW", "MEDIUM", "HIGH", "EXPOSURE_WEIGHT"]
    importance_weight: float
    value: Any
    description: str


class CustomerRiskProfile(BaseModel):
    customer_id: int
    customer_name: str
    city: str
    customer_status: str
    snapshot_date: str
    churn_probability: float
    risk_level: Literal["LOW", "MEDIUM", "HIGH"]
    risk_tier_rank: Optional[int] = None
    top_risk_factors: List[CustomerRiskFactor] = []
    model_version: str
