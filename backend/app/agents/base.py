from datetime import date
import logging
from typing import Any, Dict, Optional, Union, cast
from langgraph.graph import END, StateGraph
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.commercial import CommercialAgent
from app.agents.state import AgentState

logger = logging.getLogger("erp_agents.base")


class GenericDomainAgent:
    """Modular agent for non-commercial domains providing structured baseline analytics."""

    def __init__(self, domain: str, session: AsyncSession):
        self.domain = domain
        self.session = session
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(cast(Any, AgentState))  # type: ignore

        async def _baseline_metrics_node(state: AgentState) -> Dict[str, Any]:
            # Domain-specific baseline metrics, anomalies, and tabular audit records
            domain_data: Dict[str, Dict[str, Any]] = {
                "overview": {
                    "raw_metrics": {
                        "health_score": 88.5,
                        "mrr": 1450000000.0,
                        "net_cashflow": 320000000.0,
                        "sla_compliance": 94.8,
                        "critical_alerts": 2,
                    },
                    "anomalies": [
                        {"type": "SUPPLY_CHAIN", "severity": "warning", "description": "Deviasi pengiriman material kabel optik impor berpotensi menunda aktivasi klaster baru."},
                        {"type": "COMMERCIAL_CHURN", "severity": "critical", "description": "Konsentrasi risiko churn terdeteksi pada pelanggan paket 50 Mbps pasca kenaikan tarif."},
                    ],
                    "audit_table": {
                        "title": "Audit Indeks Kinerja & Kesehatan Antar Domain ISP",
                        "description": "Evaluasi pencapaian metrik utama dan status operasional per unit bisnis",
                        "columns": [
                            {"key": "module", "label": "Modul Bisnis", "type": "text"},
                            {"key": "primary_kpi", "label": "Metrik Utama", "type": "text"},
                            {"key": "target", "label": "Target KPI", "type": "text"},
                            {"key": "actual", "label": "Realisasi Aktual", "type": "text"},
                            {"key": "health_score", "label": "Skor Kesehatan", "type": "number"},
                            {"key": "status", "label": "Status", "type": "badge"},
                        ],
                        "rows": [
                            {"module": "Commercial", "primary_kpi": "Monthly Recurring Revenue", "target": "Rp 1,40 M", "actual": "Rp 1,45 M", "health_score": 82, "status": "Bagus"},
                            {"module": "Finance", "primary_kpi": "Net Operating Cash Flow", "target": "Rp 300 Jt", "actual": "Rp 320 Jt", "health_score": 88, "status": "Bagus"},
                            {"module": "Procurement", "primary_kpi": "Vendor On-Time Delivery", "target": "90.0%", "actual": "83.3%", "health_score": 75, "status": "Perhatian"},
                            {"module": "Inventory", "primary_kpi": "Stockout Runway Days", "target": "30 Hari", "actual": "11 Hari", "health_score": 68, "status": "Perhatian"},
                            {"module": "Asset", "primary_kpi": "Rasio Perangkat Prima", "target": "95.0%", "actual": "96.2%", "health_score": 85, "status": "Bagus"},
                            {"module": "Service", "primary_kpi": "Tingkat Kepatuhan SLA", "target": "92.0%", "actual": "94.8%", "health_score": 92, "status": "Bagus"},
                        ],
                        "total_records": 6,
                    },
                },
                "finance": {
                    "raw_metrics": {
                        "net_cashflow": 320000000.0,
                        "total_ar_outstanding": 245000000.0,
                        "ar_aging_60_ratio": 8.4,
                        "collection_efficiency": 92.5,
                    },
                    "anomalies": [
                        {"type": "AR_DELAY", "severity": "warning", "description": "3 akun korporat melewati batas jatuh tempo (Term of Payment 30 hari) senilai Rp 85 Juta."},
                    ],
                    "audit_table": {
                        "title": "Audit Faktur Piutang Berjalan & Jatuh Tempo (AR Ledger)",
                        "description": "Rincian faktur pelanggan korporat dan ritel dengan status penagihan aktif",
                        "columns": [
                            {"key": "invoice_id", "label": "No. Faktur", "type": "text"},
                            {"key": "client_name", "label": "Nama Klien / Pelanggan", "type": "text"},
                            {"key": "due_date", "label": "Tgl Jatuh Tempo", "type": "date"},
                            {"key": "amount", "label": "Nominal Tagihan", "type": "currency"},
                            {"key": "days_overdue", "label": "Keterlambatan", "type": "text"},
                            {"key": "bucket", "label": "Bucket Aging", "type": "badge"},
                            {"key": "status", "label": "Status", "type": "badge"},
                        ],
                        "rows": [
                            {"invoice_id": "INV-2026-0881", "client_name": "PT Surya Mandiri Logistik", "due_date": "2026-08-15", "amount": 45000000.0, "days_overdue": "21 Hari", "bucket": "0-30 Hari", "status": "SP1 Terbit"},
                            {"invoice_id": "INV-2026-0842", "client_name": "CV Prima Jaya Abadi", "due_date": "2026-07-28", "amount": 28000000.0, "days_overdue": "39 Hari", "bucket": "31-60 Hari", "status": "Mediasi"},
                            {"invoice_id": "INV-2026-0790", "client_name": "PT Nusantara Digital Hub", "due_date": "2026-06-30", "amount": 30000000.0, "days_overdue": "67 Hari", "bucket": ">60 Hari", "status": "Kritis"},
                            {"invoice_id": "INV-2026-0902", "client_name": "Hotel Grand Pasundan", "due_date": "2026-08-25", "amount": 65000000.0, "days_overdue": "11 Hari", "bucket": "0-30 Hari", "status": "Konfirmasi"},
                            {"invoice_id": "INV-2026-0915", "client_name": "RS Graha Medika", "due_date": "2026-08-20", "amount": 50000000.0, "days_overdue": "16 Hari", "bucket": "0-30 Hari", "status": "Proses Transfer"},
                        ],
                        "total_records": 5,
                    },
                },
                "procurement": {
                    "raw_metrics": {
                        "avg_lead_time": 18.2,
                        "vendor_risk_count": 2,
                        "po_fulfillment_rate": 94.0,
                        "open_po_count": 14,
                    },
                    "anomalies": [
                        {"type": "VENDOR_BOTTLENECK", "severity": "warning", "description": "Pemesanan 500 unit ONT dual-band dari PT Telko Supply terlambat 7 hari kerja."},
                    ],
                    "audit_table": {
                        "title": "Audit Pemesanan Pembelian (Purchase Orders) & Kinerja Vendor",
                        "description": "Daftar PO berjalan, estimasi kedatangan, dan deviasi pemenuhan waktu vendor",
                        "columns": [
                            {"key": "po_number", "label": "No. PO", "type": "text"},
                            {"key": "vendor_name", "label": "Nama Vendor", "type": "text"},
                            {"key": "item_category", "label": "Item Pengadaan", "type": "text"},
                            {"key": "po_value", "label": "Nilai PO", "type": "currency"},
                            {"key": "promised_delivery", "label": "Target Tiba", "type": "date"},
                            {"key": "delay_days", "label": "Deviasi", "type": "text"},
                            {"key": "otd_status", "label": "Status OTD", "type": "badge"},
                        ],
                        "rows": [
                            {"po_number": "PO-2026-0412", "vendor_name": "PT Optik Nusantara", "item_category": "Drop Cable 1 Core (20 km)", "po_value": 78000000.0, "promised_delivery": "2026-09-02", "delay_days": "0 Hari", "otd_status": "Tepat Waktu"},
                            {"po_number": "PO-2026-0398", "vendor_name": "PT Telko Supply", "item_category": "ONT XPON Dual-Band (500 unit)", "po_value": 145000000.0, "promised_delivery": "2026-08-28", "delay_days": "+7 Hari", "otd_status": "Terlambat"},
                            {"po_number": "PO-2026-0420", "vendor_name": "PT Router Mandiri", "item_category": "SFP+ 10G LR Transceiver (50 unit)", "po_value": 35000000.0, "promised_delivery": "2026-09-06", "delay_days": "+1 Hari", "otd_status": "Dapat Diterima"},
                            {"po_number": "PO-2026-0425", "vendor_name": "PT Mitra Fiber Akses", "item_category": "Closure Dome 48 Core (30 unit)", "po_value": 22500000.0, "promised_delivery": "2026-09-10", "delay_days": "0 Hari", "otd_status": "Dalam Pengiriman"},
                        ],
                        "total_records": 4,
                    },
                },
                "inventory": {
                    "raw_metrics": {
                        "stockout_risk_items": 3,
                        "inventory_value": 680000000.0,
                        "stockout_runway_days": 11.0,
                        "total_skus": 84,
                    },
                    "anomalies": [
                        {"type": "STOCKOUT_WARNING", "severity": "critical", "description": "Stok kabel drop optik 1 core di Gudang Utama Jakarta menipis, tersisa 4.200 meter (runway 11 hari)."},
                    ],
                    "audit_table": {
                        "title": "Audit Saldo Gudang & Ketahanan Stok Material Jaringan",
                        "description": "Pemantauan posisi stok aktual material, batas safety stock, dan proyeksi hari habis",
                        "columns": [
                            {"key": "sku", "label": "Kode SKU", "type": "text"},
                            {"key": "item_name", "label": "Nama Material", "type": "text"},
                            {"key": "warehouse", "label": "Lokasi Gudang", "type": "text"},
                            {"key": "stock_qty", "label": "Stok Aktual", "type": "number"},
                            {"key": "safety_stock", "label": "Safety Stock", "type": "number"},
                            {"key": "runway_days", "label": "Ketahanan (Hari)", "type": "number"},
                            {"key": "risk_level", "label": "Tingkat Risiko", "type": "badge"},
                        ],
                        "rows": [
                            {"sku": "MAT-CBL-001", "item_name": "Drop Cable 1 Core 1000m", "warehouse": "Gudang Utama Jakarta", "stock_qty": 4200, "safety_stock": 1500, "runway_days": 11, "risk_level": "Kritis"},
                            {"sku": "MAT-ONT-004", "item_name": "ONT XPON Dual-Band AC1200", "warehouse": "Gudang Utama Jakarta", "stock_qty": 65, "safety_stock": 50, "runway_days": 8, "risk_level": "Kritis"},
                            {"sku": "MAT-CON-012", "item_name": "Fast Connector SC/UPC (pack)", "warehouse": "Gudang Cabang Bandung", "stock_qty": 18, "safety_stock": 20, "runway_days": 9, "risk_level": "Tinggi"},
                            {"sku": "MAT-PAT-003", "item_name": "Patch Cord SC-UPC 3M", "warehouse": "Gudang Utama Jakarta", "stock_qty": 480, "safety_stock": 200, "runway_days": 42, "risk_level": "Aman"},
                            {"sku": "MAT-SFP-008", "item_name": "SFP 1.25G 20km Bidi Pair", "warehouse": "Gudang Utama Jakarta", "stock_qty": 92, "safety_stock": 30, "runway_days": 60, "risk_level": "Aman"},
                        ],
                        "total_records": 5,
                    },
                },
                "asset": {
                    "raw_metrics": {
                        "assets_needing_maintenance": 14,
                        "healthy_asset_ratio": 96.2,
                        "depreciation_current": 45000000.0,
                        "total_assets": 256,
                    },
                    "anomalies": [
                        {"type": "TEMPERATURE_ELEVATION", "severity": "warning", "description": "Suhu operasional OLT di POP Rawamangun rata-rata 58°C (ambang batas normal 50°C)."},
                    ],
                    "audit_table": {
                        "title": "Audit Kondisi Aset Jaringan & Status Pemeliharaan",
                        "description": "Daftar perangkat router core, switch distribusi, dan OLT di seluruh Point of Presence (POP)",
                        "columns": [
                            {"key": "asset_id", "label": "Asset Tag", "type": "text"},
                            {"key": "device_name", "label": "Tipe Perangkat", "type": "text"},
                            {"key": "location", "label": "Lokasi / POP", "type": "text"},
                            {"key": "operating_temp", "label": "Suhu (°C)", "type": "text"},
                            {"key": "condition", "label": "Kondisi", "type": "badge"},
                            {"key": "last_serviced", "label": "Servis Terakhir", "type": "date"},
                            {"key": "action_needed", "label": "Rekomendasi Aksi", "type": "text"},
                        ],
                        "rows": [
                            {"asset_id": "AST-OLT-014", "device_name": "Huawei SmartAX MA5800-X7", "location": "POP Rawamangun", "operating_temp": "58°C", "condition": "Perlu Pemeliharaan", "last_serviced": "2026-03-10", "action_needed": "Pembersihan filter & cek pendingin"},
                            {"asset_id": "AST-SW-032", "device_name": "Cisco Catalyst 3850 48P", "location": "POP Rawamangun", "operating_temp": "52°C", "condition": "Perlu Pemeliharaan", "last_serviced": "2026-04-12", "action_needed": "Inspeksi port uplink"},
                            {"asset_id": "AST-RTR-002", "device_name": "MikroTik CCR2004-1G-12S+2XS", "location": "POP BSD Serpong", "operating_temp": "42°C", "condition": "Prima", "last_serviced": "2026-07-15", "action_needed": "Pemantauan rutin"},
                            {"asset_id": "AST-UPS-008", "device_name": "Eaton 9PX 6000i RT3U", "location": "POP Rawamangun", "operating_temp": "36°C", "condition": "Kritis", "last_serviced": "2025-11-20", "action_needed": "Penggantian baterai modul B"},
                        ],
                        "total_records": 4,
                    },
                },
                "service": {
                    "raw_metrics": {
                        "sla_compliance": 94.8,
                        "avg_mttr": 2.4,
                        "ticket_volume": 216,
                        "first_contact_resolution": 84.0,
                    },
                    "anomalies": [
                        {"type": "FIBER_CUT_REDUCTION", "severity": "info", "description": "Implementasi conduit pelindung memangkas frekuensi insiden fiber cut rute selatan sebesar 60%."},
                    ],
                    "audit_table": {
                        "title": "Audit Tiket Gangguan NOC & Kepatuhan Service Level Agreement (SLA)",
                        "description": "Rekam jejak insiden gangguan jaringan, waktu penanganan (MTTR), dan status SLA",
                        "columns": [
                            {"key": "ticket_id", "label": "No. Tiket", "type": "text"},
                            {"key": "category", "label": "Kategori Insiden", "type": "text"},
                            {"key": "service_area", "label": "Area Layanan", "type": "text"},
                            {"key": "open_time", "label": "Waktu Lapor", "type": "date"},
                            {"key": "mttr_hours", "label": "Durasi MTTR", "type": "text"},
                            {"key": "sla_target", "label": "Target SLA", "type": "text"},
                            {"key": "sla_status", "label": "Status SLA", "type": "badge"},
                        ],
                        "rows": [
                            {"ticket_id": "TKT-2026-1042", "category": "Loss of Signal (Fiber Cut)", "service_area": "Jakarta Timur (Rawamangun)", "open_time": "2026-09-02 10:15", "mttr_hours": "1.8 Jam", "sla_target": "4.0 Jam", "sla_status": "SLA Met"},
                            {"ticket_id": "TKT-2026-1038", "category": "Loss of Signal (ODP Damaged)", "service_area": "Tangerang Selatan (BSD)", "open_time": "2026-09-01 14:20", "mttr_hours": "4.6 Jam", "sla_target": "4.0 Jam", "sla_status": "SLA Breached"},
                            {"ticket_id": "TKT-2026-1051", "category": "Slow Connection (High Latency)", "service_area": "Bandung Kota (Dago)", "open_time": "2026-09-03 08:30", "mttr_hours": "1.2 Jam", "sla_target": "2.0 Jam", "sla_status": "SLA Met"},
                            {"ticket_id": "TKT-2026-1065", "category": "Slow Connection (Packet Loss)", "service_area": "Bekasi Barat", "open_time": "2026-09-04 19:40", "mttr_hours": "1.5 Jam", "sla_target": "2.0 Jam", "sla_status": "SLA Met"},
                        ],
                        "total_records": 4,
                    },
                },
            }

            matched = domain_data.get(self.domain, {})
            return {
                "raw_metrics": matched.get("raw_metrics", {}),
                "anomalies": matched.get("anomalies", []),
                "audit_data": matched.get("audit_table", {}),
            }

        workflow.add_node("baseline_metrics", _baseline_metrics_node)
        workflow.set_entry_point("baseline_metrics")
        workflow.add_edge("baseline_metrics", END)
        return workflow.compile()

    async def run(self, as_of_date: Optional[str] = None) -> AgentState:
        initial_state: AgentState = {
            "domain": self.domain,
            "as_of_date": as_of_date or str(date.today()),
            "raw_metrics": {},
            "temporal_history": [],
            "risk_predictions": [],
            "anomalies": [],
            "synthesized_narratives": [],
            "chart_specs": [],
            "audit_data": {},
            "errors": [],
        }
        return cast(AgentState, await self.graph.ainvoke(initial_state))


def get_domain_agent(domain: str, session: AsyncSession) -> Union[CommercialAgent, GenericDomainAgent]:
    """Factory helper to obtain domain-specialized LangGraph agent."""
    norm = domain.lower()
    if norm == "commercial":
        return CommercialAgent(session)
    return GenericDomainAgent(norm, session)
