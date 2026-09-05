from typing import List, Optional
from pydantic import BaseModel, Field


class DatabaseComponentHealth(BaseModel):
    status: str = Field(..., description="Status koneksi database (connected / disconnected)")
    latency_ms: Optional[float] = Field(default=None, description="Latensi query ping ke database dalam milidetik")
    pool_size: int = Field(..., description="Ukuran pool koneksi database saat ini")
    active_connections: int = Field(default=0, description="Jumlah koneksi yang sedang aktif digunakan")


class FeatureStoreComponentHealth(BaseModel):
    status: str = Field(..., description="Status skema Feature Store (ready / uninitialized)")
    schemas: List[str] = Field(default=["staging", "feature_store"], description="Daftar skema terdaftar")


class HealthComponents(BaseModel):
    database: DatabaseComponentHealth
    feature_store: FeatureStoreComponentHealth


class HealthResponse(BaseModel):
    status: str = Field(..., description="Status liveness keseluruhan aplikasi (healthy / degraded / unhealthy)")
    timestamp: str = Field(..., description="Waktu pengecekan kesehatan format ISO-8601")
    version: str = Field(default="0.1.0", description="Versi rilis aplikasi backend")
    environment: str = Field(..., description="Nama environment aktif (development / staging / production)")
    components: HealthComponents
