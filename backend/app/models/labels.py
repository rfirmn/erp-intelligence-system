from datetime import date
from typing import ClassVar, Optional
from sqlmodel import Field, SQLModel


class LabelChurnEvent(SQLModel, table=True):
    __tablename__: ClassVar[str] = "label_churn_event"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    customer_id: int = Field(..., primary_key=True, index=True)
    feature_snapshot_date: date = Field(..., primary_key=True)
    label_window_start: date = Field(...)
    label_window_end: date = Field(...)
    churned: Optional[bool] = Field(default=None)
    churn_date: Optional[date] = Field(default=None)
