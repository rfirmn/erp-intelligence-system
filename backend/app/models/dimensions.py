from datetime import date, datetime
from typing import ClassVar, Optional
from sqlmodel import Field, SQLModel


class DimCustomer(SQLModel, table=True):
    __tablename__: ClassVar[str] = "dim_customer"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    customer_key: Optional[int] = Field(default=None, primary_key=True)
    customer_id: int = Field(..., index=True)
    customer_name: Optional[str] = Field(default=None, max_length=255)
    city: Optional[str] = Field(default=None, max_length=100)
    installation_date: Optional[date] = Field(default=None)
    status: Optional[str] = Field(default=None, max_length=50)  # ACTIVE / SUSPENDED / TERMINATED
    valid_from: date = Field(...)
    valid_to: Optional[date] = Field(default=None)
    is_current: bool = Field(default=True, index=True)
    source_updated_at: Optional[datetime] = Field(default=None)


class DimPackage(SQLModel, table=True):
    __tablename__: ClassVar[str] = "dim_package"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    package_key: Optional[int] = Field(default=None, primary_key=True)
    package_id: int = Field(..., index=True)
    package_name: Optional[str] = Field(default=None, max_length=150)
    speed_mbps: Optional[int] = Field(default=None)
    monthly_price: Optional[float] = Field(default=None)
    valid_from: date = Field(...)
    valid_to: Optional[date] = Field(default=None)
    is_current: bool = Field(default=True, index=True)


class DimDate(SQLModel, table=True):
    __tablename__: ClassVar[str] = "dim_date"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    date_key: date = Field(..., primary_key=True)
    year: int = Field(...)
    month: int = Field(...)
    quarter: int = Field(...)
    week_of_year: int = Field(...)
    day_of_week: int = Field(...)
    is_month_end: bool = Field(default=False)
    is_billing_cycle_end: bool = Field(default=False)
