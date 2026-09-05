from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
import uuid
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationMeta(BaseModel):
    page: int = Field(..., description="Nomor halaman aktif (1-indexed)")
    page_size: int = Field(..., description="Jumlah data per halaman")
    total_records: int = Field(..., description="Total keseluruhan data")
    total_pages: int = Field(..., description="Total halaman yang tersedia")


class ResponseMeta(BaseModel):
    request_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Pengenal unik transaksi request (UUIDv4) untuk tracing",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="Waktu pembuatan respons dalam format ISO-8601 UTC",
    )
    version: str = Field(default="v1", description="Versi API yang melayani request")
    pagination: Optional[PaginationMeta] = Field(
        default=None, description="Metadata pagination (jika respons mengembalikan daftar data)"
    )


class ErrorDetail(BaseModel):
    field: Optional[str] = Field(default=None, description="Nama field yang mengalami kegagalan validasi")
    issue: str = Field(..., description="Deskripsi permasalahan validasi")


class ResponseError(BaseModel):
    code: str = Field(..., description="Katalog kode error standar (e.g. VALIDATION_ERROR, NOT_FOUND)")
    message: str = Field(..., description="Pesan deskriptif error yang ramah pengguna")
    details: Optional[List[ErrorDetail]] = Field(default=None, description="Rincian error per-field")


class ResponseEnvelope(BaseModel, Generic[T]):
    success: bool = Field(..., description="Status keberhasilan operasi")
    data: Optional[T] = Field(default=None, description="Payload data utama respons")
    meta: ResponseMeta = Field(default_factory=ResponseMeta, description="Metadata pendukung")
    error: Optional[ResponseError] = Field(default=None, description="Objek error jika operasi gagal")


def create_meta(request_id: Optional[str] = None, pagination: Optional[PaginationMeta] = None) -> ResponseMeta:
    return ResponseMeta(
        request_id=request_id or str(uuid.uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="v1",
        pagination=pagination,
    )


def success_response(
    data: Any,
    request_id: Optional[str] = None,
    pagination: Optional[PaginationMeta] = None,
) -> Dict[str, Any]:
    """Helper to produce a standard success dictionary."""
    meta = create_meta(request_id=request_id, pagination=pagination)
    return {
        "success": True,
        "data": data,
        "meta": meta.model_dump(),
        "error": None,
    }


def error_response(
    code: str,
    message: str,
    details: Optional[List[Dict[str, Any]]] = None,
    request_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Helper to produce a standard error dictionary."""
    meta = create_meta(request_id=request_id)
    return {
        "success": False,
        "data": None,
        "meta": meta.model_dump(),
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
        },
    }
