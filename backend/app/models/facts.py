from datetime import date
from typing import ClassVar, Optional
import uuid
from sqlmodel import Field, SQLModel


class FactSubscriptionSnapshot(SQLModel, table=True):
    __tablename__: ClassVar[str] = "fact_subscription_snapshot"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    snapshot_date: date = Field(..., primary_key=True)
    customer_key: int = Field(..., primary_key=True, foreign_key="feature_store.dim_customer.customer_key")
    package_key: Optional[int] = Field(default=None, foreign_key="feature_store.dim_package.package_key")
    subscription_status: Optional[str] = Field(default=None, max_length=50)
    tenure_days: Optional[int] = Field(default=None)
    monthly_fee: Optional[float] = Field(default=None)
    is_active: Optional[bool] = Field(default=None)
    batch_id: uuid.UUID = Field(...)


class FactBillingMonthly(SQLModel, table=True):
    __tablename__: ClassVar[str] = "fact_billing_monthly"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    invoice_period: date = Field(..., primary_key=True)
    customer_key: int = Field(..., primary_key=True, foreign_key="feature_store.dim_customer.customer_key")
    invoiced_amount: Optional[float] = Field(default=None)
    paid_amount: Optional[float] = Field(default=None)
    payment_status: Optional[str] = Field(default=None, max_length=50)
    days_late: Optional[int] = Field(default=None)
    batch_id: uuid.UUID = Field(...)


class FactCashflowMonthly(SQLModel, table=True):
    __tablename__: ClassVar[str] = "fact_cashflow_monthly"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    period_month: date = Field(..., primary_key=True)
    total_revenue: Optional[float] = Field(default=None)
    total_expense: Optional[float] = Field(default=None)
    accounts_receivable: Optional[float] = Field(default=None)
    accounts_payable: Optional[float] = Field(default=None)
    net_cashflow: Optional[float] = Field(default=None)
    batch_id: uuid.UUID = Field(...)


class FactInventorySnapshot(SQLModel, table=True):
    __tablename__: ClassVar[str] = "fact_inventory_snapshot"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    snapshot_date: date = Field(..., primary_key=True)
    warehouse_id: int = Field(..., primary_key=True)
    item_id: int = Field(..., primary_key=True)
    quantity_on_hand: Optional[int] = Field(default=None)
    batch_id: uuid.UUID = Field(...)
