from datetime import date
from typing import ClassVar, Optional
import uuid
from sqlmodel import Field, SQLModel


class FeatureCustomerChurn(SQLModel, table=True):
    __tablename__: ClassVar[str] = "feature_customer_churn"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    snapshot_date: date = Field(..., primary_key=True)
    customer_id: int = Field(..., primary_key=True, index=True)
    tenure_months: Optional[float] = Field(default=None)
    monthly_fee_current: Optional[float] = Field(default=None)
    package_speed_mbps: Optional[int] = Field(default=None)
    late_payment_count_3m: Optional[int] = Field(default=None)
    late_payment_count_6m: Optional[int] = Field(default=None)
    avg_payment_delay_days_3m: Optional[float] = Field(default=None)
    payment_status_trend: Optional[str] = Field(default=None, max_length=50)  # IMPROVING / STABLE / WORSENING
    downgrade_flag_6m: Optional[bool] = Field(default=None)
    batch_id: uuid.UUID = Field(...)


class FeatureCashflowForecast(SQLModel, table=True):
    __tablename__: ClassVar[str] = "feature_cashflow_forecast"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    snapshot_date: date = Field(..., primary_key=True)
    total_revenue_current: Optional[float] = Field(default=None)
    total_expense_current: Optional[float] = Field(default=None)
    net_cashflow_current: Optional[float] = Field(default=None)
    revenue_trend_3m: Optional[float] = Field(default=None)
    ar_aging_30: Optional[float] = Field(default=None)
    ar_aging_60: Optional[float] = Field(default=None)
    ar_aging_90plus: Optional[float] = Field(default=None)
    batch_id: uuid.UUID = Field(...)
