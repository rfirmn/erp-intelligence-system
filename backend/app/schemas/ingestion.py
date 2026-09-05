from typing import List, Optional
from pydantic import BaseModel, Field


class JobTriggerRequest(BaseModel):
    limit: int = Field(
        default=5000,
        ge=1,
        le=50000,
        description="Maksimal jumlah baris data yang diekstrak per batch",
    )
    force_full_refresh: bool = Field(
        default=False,
        description="Jika true, abaikan watermark dan lakukan refresh menyeluruh",
    )


class JobTriggerResponse(BaseModel):
    batch_id: str = Field(..., description="UUID identifier batch yang dieksekusi")
    job_name: str = Field(..., description="Nama pipeline job yang dijalankan")
    is_mock_data: bool = Field(
        ...,
        description="TANDA JELAS: True jika data diproduksi dari Mock ERP Generator, False jika Live ERP",
    )
    source_type: str = Field(
        ..., description="'MOCK_GENERATOR' atau 'LIVE_ERP'"
    )
    status: str = Field(..., description="Status akhir batch (SUCCESS / FAILED)")
    rows_extracted: int = Field(..., description="Total baris data yang diekstrak")
    rows_staged: int = Field(..., description="Total baris data yang dimuat ke staging layer")
    rows_dimension: Optional[int] = Field(
        default=None, description="Total perubahan dimensi (SCD2)"
    )
    rows_fact: Optional[int] = Field(
        default=None, description="Total fact snapshots/monthly yang tersimpan"
    )
    rows_features: Optional[int] = Field(
        default=None, description="Total baris fitur ML yang diperbarui"
    )
    invoices_count: Optional[int] = Field(default=None)
    payments_count: Optional[int] = Field(default=None)
    watermark_start: Optional[str] = Field(default=None)
    watermark_end: str = Field(...)


class BatchLogItem(BaseModel):
    batch_id: str
    source_table: str
    watermark_start: Optional[str] = None
    watermark_end: Optional[str] = None
    status: str
    is_mock_data: bool = Field(
        ...,
        description="True jika log batch dieksekusi dengan mock data generator",
    )
    row_count: int
    started_at: str
    finished_at: Optional[str] = None


class DataQualityLogItem(BaseModel):
    log_id: int
    batch_id: Optional[str] = None
    check_name: str
    table_name: str
    status: str
    details: Optional[str] = None
    checked_at: str


class SchedulerJobItem(BaseModel):
    id: str
    name: str
    next_run_time: Optional[str] = None
    trigger: str
