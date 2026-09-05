from datetime import date, datetime, timezone
from typing import ClassVar, Optional
import uuid
from sqlmodel import Field, SQLModel


class StgCustomerSubscription(SQLModel, table=True):
    __tablename__: ClassVar[str] = "stg_customer_subscription"  # type: ignore
    __table_args__ = {"schema": "staging"}

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(..., index=True)
    customer_id: Optional[int] = Field(default=None)
    package_id: Optional[int] = Field(default=None)
    subscription_no: Optional[str] = Field(default=None)
    start_date: Optional[date] = Field(default=None)
    end_date: Optional[date] = Field(default=None)
    monthly_fee: Optional[float] = Field(default=None)
    billing_day: Optional[int] = Field(default=None)
    status: Optional[str] = Field(default=None)
    source_updated_at: Optional[datetime] = Field(default=None)
    batch_id: uuid.UUID = Field(...)
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StgSalesInvoice(SQLModel, table=True):
    __tablename__: ClassVar[str] = "stg_sales_invoice"  # type: ignore
    __table_args__ = {"schema": "staging"}

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(..., index=True)
    customer_subscription_id: Optional[int] = Field(default=None)
    invoice_number: Optional[str] = Field(default=None)
    invoice_period: Optional[date] = Field(default=None)
    invoice_date: Optional[date] = Field(default=None)
    due_date: Optional[date] = Field(default=None)
    total_amount: Optional[float] = Field(default=None)
    payment_status: Optional[str] = Field(default=None)
    source_updated_at: Optional[datetime] = Field(default=None)
    batch_id: uuid.UUID = Field(...)
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StgSalesPayment(SQLModel, table=True):
    __tablename__: ClassVar[str] = "stg_sales_payment"  # type: ignore
    __table_args__ = {"schema": "staging"}

    id: Optional[int] = Field(default=None, primary_key=True)
    source_id: int = Field(..., index=True)
    sales_invoice_id: Optional[int] = Field(default=None)
    payment_date: Optional[date] = Field(default=None)
    amount: Optional[float] = Field(default=None)
    payment_status: Optional[str] = Field(default=None)
    source_created_at: Optional[datetime] = Field(default=None)
    batch_id: uuid.UUID = Field(...)
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class StgStock(SQLModel, table=True):
    __tablename__: ClassVar[str] = "stg_stock"  # type: ignore
    __table_args__ = {"schema": "staging"}

    id: Optional[int] = Field(default=None, primary_key=True)
    warehouse_id: int = Field(...)
    item_id: int = Field(...)
    quantity: Optional[int] = Field(default=None)
    last_updated: Optional[datetime] = Field(default=None)
    batch_id: uuid.UUID = Field(...)
    loaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
