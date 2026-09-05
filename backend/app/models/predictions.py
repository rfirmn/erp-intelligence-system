from datetime import date, datetime
from typing import Any, ClassVar, List, Optional
from sqlalchemy import Column, DateTime, JSON
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utc_now


class PredictionCustomerChurn(SQLModel, table=True):
    __tablename__: ClassVar[str] = "prediction_customer_churn"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    snapshot_date: date = Field(..., primary_key=True)
    customer_id: int = Field(..., primary_key=True, index=True)
    churn_probability: float = Field(..., description="Probabilitas churn 0.0 - 1.0")
    risk_level: str = Field(..., max_length=20, index=True, description="LOW / MEDIUM / HIGH")
    risk_tier_rank: Optional[int] = Field(default=None, description="Prioritas ranking risiko")
    top_risk_factors: Optional[List[Any]] = Field(
        default=None,
        sa_column=Column(JSON),
        description="Faktor pendorong risiko (SHAP/feature contribution)",
    )
    model_version: str = Field(..., max_length=50, description="Versi model ML yang digunakan")
    created_at: datetime = Field(
        default_factory=utc_now,
        sa_column=Column(DateTime(timezone=False), nullable=False),
        description="Waktu kalkulasi inferensi dibuat",
    )
