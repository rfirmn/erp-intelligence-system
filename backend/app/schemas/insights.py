from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class KeyMetric(BaseModel):
    key: str = Field(..., description="Identifier unik metrik (e.g. mrr, churn_risk_count)")
    label: str = Field(..., description="Label human-readable metrik untuk ditampilkan di card")
    value: float = Field(..., description="Nilai kuantitatif numerik mentah")
    formatted_value: str = Field(..., description="String nilai berformat untuk kemudahan rendering UI")
    unit: str = Field(..., description="Satuan nilai metrik (e.g. IDR, customers, %)")
    change_percentage: Optional[float] = Field(default=None, description="Persentase perubahan dari periode lalu")
    trend: Optional[Literal["up", "down", "neutral"]] = Field(default=None, description="Arah tren pergerakan metrik")
    status: Optional[Literal["good", "warning", "critical"]] = Field(default=None, description="Indikator warna status")


class NarrativeInsight(BaseModel):
    id: str = Field(..., description="ID unik wawasan (e.g. ins-comm-001)")
    domain: str = Field(..., description="Domain bisnis asal wawasan")
    severity: Literal["info", "warning", "critical"] = Field(default="info", description="Tingkat keparahan temuan")
    title: str = Field(..., description="Judul ringkas temuan wawasan")
    narrative: str = Field(..., description="Penjelasan mendalam berbasis alasan agen AI")
    suggested_actions: List[str] = Field(default=[], description="Daftar tindakan konkret yang direkomendasikan")


class Visualization(BaseModel):
    chart_id: str = Field(..., description="Identifier unik grafik")
    title: str = Field(..., description="Judul grafik")
    description: str = Field(..., description="Subjudul atau keterangan data grafik")
    chart_library: Literal["vega-lite", "plotly"] = Field(default="vega-lite", description="Library rendering grafik")
    spec: Dict[str, Any] = Field(..., description="Spesifikasi JSON Vega-Lite v5 atau Plotly")
    data: Optional[List[Dict[str, Any]]] = Field(default=None, description="Dataset yang di-bind ke grafik")


class ModelMetadata(BaseModel):
    model_name: str = Field(..., description="Nama model machine learning yang digunakan")
    version: str = Field(..., description="Versi model")
    prediction_window: Optional[str] = Field(default=None, description="Jendela prediksi (e.g. 30_days, 1_quarter)")
    confidence_score: Optional[float] = Field(default=None, description="Skor akurasi / keyakinan / ROC-AUC")
    last_trained_at: Optional[str] = Field(default=None, description="Waktu pelatihan terakhir model")


class InsightPackage(BaseModel):
    module: str = Field(..., description="Nama modul bisnis (overview, commercial, finance, dll.)")
    as_of_date: str = Field(..., description="Tanggal data dasar snapshot (YYYY-MM-DD)")
    executive_summary: str = Field(..., description="Narasi ringkasan eksekutif 2-3 kalimat")
    key_metrics: List[KeyMetric] = Field(default=[], description="Daftar kartu KPI utama")
    narrative_insights: List[NarrativeInsight] = Field(default=[], description="Daftar wawasan temuan mendalam")
    visualizations: List[Visualization] = Field(default=[], description="Daftar spesifikasi grafik visualisasi")
    model_metadata: List[ModelMetadata] = Field(default=[], description="Metadata model prediktif penunjang")
    generated_at: str = Field(..., description="Timestamp kompilasi paket wawasan")
