from datetime import datetime, timezone
from typing import ClassVar, Optional
import uuid
from sqlmodel import Field, SQLModel


class ETLBatchLog(SQLModel, table=True):
    __tablename__: ClassVar[str] = "etl_batch_log"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    batch_id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    source_table: str = Field(..., max_length=100)
    watermark_start: Optional[datetime] = Field(default=None)
    watermark_end: Optional[datetime] = Field(default=None)
    row_count: Optional[int] = Field(default=None)
    status: str = Field(default="PENDING", max_length=50)  # SUCCESS / FAILED / PARTIAL
    started_at: Optional[datetime] = Field(default=None)
    finished_at: Optional[datetime] = Field(default=None)


from app.core.datetime_utils import utc_now


class DataQualityLog(SQLModel, table=True):
    __tablename__: ClassVar[str] = "data_quality_log"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    id: Optional[int] = Field(default=None, primary_key=True)
    batch_id: Optional[uuid.UUID] = Field(default=None, foreign_key="feature_store.etl_batch_log.batch_id")
    check_name: str = Field(..., max_length=150)
    table_name: str = Field(..., max_length=100)
    status: str = Field(..., max_length=50)  # PASS / FAIL / WARN
    details: Optional[str] = Field(default=None)
    checked_at: datetime = Field(default_factory=utc_now)
