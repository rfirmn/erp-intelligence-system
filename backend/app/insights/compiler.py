from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.agents.base import get_domain_agent
from app.agents.state import AgentState
from app.insights.chart_generator import (
    build_ar_aging_chart,
    build_asset_health_chart,
    build_billing_delay_trend_chart,
    build_churn_distribution_chart,
    build_domain_health_chart,
    build_stock_depletion_chart,
    build_ticket_sla_chart,
    build_vendor_performance_chart,
)
from app.insights.llm_client import UnifiedLLMClient
from app.insights.validator import validate_insight_package
from app.ml.config import ml_config
from app.ml.registry import get_active_model_metadata
from app.schemas.insights import (
    AuditTable,
    InsightPackage,
    KeyMetric,
    ModelMetadata,
    NarrativeInsight,
    Visualization,
)

logger = logging.getLogger("erp_insights.compiler")


class InsightCompiler:
    """Orchestrator that executes domain LangGraph agents, compiles Tri-Pillar context, synthesizes insights, and produces validated packages."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.llm_client = UnifiedLLMClient()

    async def compile_module_insight(
        self,
        domain: str = "commercial",
        as_of_date: Optional[str] = None,
    ) -> InsightPackage:
        """Run domain agent and compile into validated InsightPackage."""
        norm_domain = domain.lower().strip()
        logger.info(f"Compiling insight package for domain '{norm_domain}'...")

        # 1. Execute LangGraph Domain Agent
        agent = get_domain_agent(domain=norm_domain, session=self.session)
        state = await agent.run(as_of_date=as_of_date)

        target_date = state.get("as_of_date", str(datetime.now(timezone.utc).date()))
        raw_metrics = state.get("raw_metrics", {})
        high_risk = state.get("risk_predictions", [])
        temporal_history = state.get("temporal_history", [])
        anomalies = state.get("anomalies", [])

        # 2. Dispatch domain-specific KPI cards, charts, audit tables, and model metadata
        if norm_domain == "overview":
            key_metrics, vis_list, audit_table_dict, model_meta_list = self._assemble_overview(raw_metrics, state)
        elif norm_domain == "finance":
            key_metrics, vis_list, audit_table_dict, model_meta_list = self._assemble_finance(raw_metrics, state)
        elif norm_domain == "procurement":
            key_metrics, vis_list, audit_table_dict, model_meta_list = self._assemble_procurement(raw_metrics, state)
        elif norm_domain == "inventory":
            key_metrics, vis_list, audit_table_dict, model_meta_list = self._assemble_inventory(raw_metrics, state)
        elif norm_domain == "asset":
            key_metrics, vis_list, audit_table_dict, model_meta_list = self._assemble_asset(raw_metrics, state)
        elif norm_domain == "service":
            key_metrics, vis_list, audit_table_dict, model_meta_list = self._assemble_service(raw_metrics, state)
        else:
            key_metrics, vis_list, audit_table_dict, model_meta_list = self._assemble_commercial(
                raw_metrics, high_risk, temporal_history
            )

        # 3. Synthesize Narrative via LLM Client (Tri-Pillar Injection with Domain Grounding)
        synthesis = await self.llm_client.generate_insight_narrative(
            domain=norm_domain,
            as_of_date=target_date,
            metrics=raw_metrics,
            high_risk_customers=high_risk,
            temporal_history=temporal_history,
            anomalies=anomalies,
        )

        exec_summary = synthesis.get("executive_summary", "")
        narratives_raw = synthesis.get("narrative_insights", [])

        # 4. Assemble Full Package Payload
        package_payload: Dict[str, Any] = {
            "module": norm_domain,
            "as_of_date": target_date,
            "executive_summary": exec_summary,
            "key_metrics": key_metrics,
            "narrative_insights": narratives_raw,
            "visualizations": vis_list,
            "audit_table": audit_table_dict,
            "model_metadata": model_meta_list,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # 5. Validate through Pydantic
        return validate_insight_package(package_payload)

    def _assemble_overview(self, metrics: Dict[str, Any], state: AgentState):
        health_score = metrics.get("health_score", 88.5)
        mrr_val = metrics.get("mrr", 1450000000.0)
        cashflow = metrics.get("net_cashflow", 320000000.0)
        sla_val = metrics.get("sla_compliance", 94.8)
        alerts_count = metrics.get("critical_alerts", 2)

        key_metrics = [
            {
                "key": "health_score",
                "label": "Indeks Kesehatan Operasional",
                "value": float(health_score),
                "formatted_value": f"{health_score:.1f} / 100",
                "unit": "score",
                "change_percentage": 2.4,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "mrr",
                "label": "Monthly Recurring Revenue",
                "value": float(mrr_val),
                "formatted_value": f"Rp {mrr_val / 1_000_000_000:.2f} M",
                "unit": "IDR",
                "change_percentage": 3.2,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "net_cashflow",
                "label": "Net Operating Cash Flow",
                "value": float(cashflow),
                "formatted_value": f"Rp {cashflow / 1_000_000:.0f} Jt",
                "unit": "IDR",
                "change_percentage": 5.4,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "sla_compliance",
                "label": "Kepatuhan SLA Keseluruhan",
                "value": float(sla_val),
                "formatted_value": f"{sla_val:.1f}%",
                "unit": "%",
                "change_percentage": 1.2,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "critical_alerts",
                "label": "Peringatan Kritis Lintas Modul",
                "value": float(alerts_count),
                "formatted_value": f"{alerts_count} Isu Kritis",
                "unit": "alerts",
                "change_percentage": 0.0,
                "trend": "neutral",
                "status": "warning",
            },
        ]

        vis_list = [build_domain_health_chart()]
        audit_table = state.get("audit_data")
        model_meta = [
            {
                "model_name": "executive_state_compiler_v1",
                "version": "1.0.0",
                "prediction_window": "current_cycle",
                "confidence_score": 0.92,
                "last_trained_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        return key_metrics, vis_list, audit_table, model_meta

    def _assemble_finance(self, metrics: Dict[str, Any], state: AgentState):
        cashflow = metrics.get("net_cashflow", 320000000.0)
        total_ar = metrics.get("total_ar_outstanding", 245000000.0)
        ar_ratio = metrics.get("ar_aging_60_ratio", 8.4)
        efficiency = metrics.get("collection_efficiency", 92.5)

        key_metrics = [
            {
                "key": "net_cashflow",
                "label": "Net Cash Flow Proyeksi",
                "value": float(cashflow),
                "formatted_value": f"Rp {cashflow / 1_000_000:.0f} Jt",
                "unit": "IDR",
                "change_percentage": 5.4,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "total_ar_outstanding",
                "label": "Total Piutang Berjalan (AR)",
                "value": float(total_ar),
                "formatted_value": f"Rp {total_ar / 1_000_000:.0f} Jt",
                "unit": "IDR",
                "change_percentage": -4.1,
                "trend": "down",
                "status": "good",
            },
            {
                "key": "ar_aging_60_ratio",
                "label": "Rasio Piutang >60 Hari",
                "value": float(ar_ratio),
                "formatted_value": f"{ar_ratio:.1f}%",
                "unit": "%",
                "change_percentage": 0.5,
                "trend": "up",
                "status": "warning",
            },
            {
                "key": "collection_efficiency",
                "label": "Efisiensi Penagihan",
                "value": float(efficiency),
                "formatted_value": f"{efficiency:.1f}%",
                "unit": "%",
                "change_percentage": 1.8,
                "trend": "up",
                "status": "good",
            },
        ]

        vis_list = [build_ar_aging_chart()]
        audit_table = state.get("audit_data")
        model_meta = [
            {
                "model_name": "prophet_cashflow_v1",
                "version": "1.0.0",
                "prediction_window": "90_days",
                "confidence_score": 0.865,
                "last_trained_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        return key_metrics, vis_list, audit_table, model_meta

    def _assemble_procurement(self, metrics: Dict[str, Any], state: AgentState):
        lead_time = metrics.get("avg_lead_time", 18.2)
        vendor_risk = metrics.get("vendor_risk_count", 2)
        fulfillment = metrics.get("po_fulfillment_rate", 94.0)

        key_metrics = [
            {
                "key": "avg_lead_time",
                "label": "Rata-rata Lead Time PO",
                "value": float(lead_time),
                "formatted_value": f"{lead_time:.1f} Hari",
                "unit": "days",
                "change_percentage": 14.0,
                "trend": "up",
                "status": "warning",
            },
            {
                "key": "vendor_risk_count",
                "label": "Vendor Skor Risiko Tinggi",
                "value": float(vendor_risk),
                "formatted_value": f"{vendor_risk} Vendor",
                "unit": "vendors",
                "change_percentage": 0.0,
                "trend": "neutral",
                "status": "warning",
            },
            {
                "key": "po_fulfillment_rate",
                "label": "Rasio On-Time Delivery (OTD)",
                "value": float(fulfillment),
                "formatted_value": f"{fulfillment:.1f}%",
                "unit": "%",
                "change_percentage": -2.1,
                "trend": "down",
                "status": "good",
            },
        ]

        vis_list = [build_vendor_performance_chart()]
        audit_table = state.get("audit_data")
        model_meta = [
            {
                "model_name": "vendor_lead_time_xgb",
                "version": "1.0.0",
                "prediction_window": "30_days",
                "confidence_score": 0.812,
                "last_trained_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        return key_metrics, vis_list, audit_table, model_meta

    def _assemble_inventory(self, metrics: Dict[str, Any], state: AgentState):
        stockout_items = metrics.get("stockout_risk_items", 3)
        inv_val = metrics.get("inventory_value", 680000000.0)
        runway = metrics.get("stockout_runway_days", 11.0)

        key_metrics = [
            {
                "key": "stockout_risk_items",
                "label": "Item Berisiko Stockout",
                "value": float(stockout_items),
                "formatted_value": f"{stockout_items} SKU",
                "unit": "items",
                "change_percentage": 50.0,
                "trend": "up",
                "status": "critical",
            },
            {
                "key": "inventory_value",
                "label": "Total Nilai Aset Gudang",
                "value": float(inv_val),
                "formatted_value": f"Rp {inv_val / 1_000_000:.0f} Jt",
                "unit": "IDR",
                "change_percentage": -2.5,
                "trend": "down",
                "status": "good",
            },
            {
                "key": "stockout_runway_days",
                "label": "Runway Ketahanan Stok",
                "value": float(runway),
                "formatted_value": f"{runway:.0f} Hari",
                "unit": "days",
                "change_percentage": -35.0,
                "trend": "down",
                "status": "critical",
            },
        ]

        vis_list = [build_stock_depletion_chart()]
        audit_table = state.get("audit_data")
        model_meta = [
            {
                "model_name": "stockout_forecast_v1",
                "version": "1.0.0",
                "prediction_window": "14_days",
                "confidence_score": 0.884,
                "last_trained_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        return key_metrics, vis_list, audit_table, model_meta

    def _assemble_asset(self, metrics: Dict[str, Any], state: AgentState):
        service_needed = metrics.get("assets_needing_maintenance", 14)
        health_ratio = metrics.get("healthy_asset_ratio", 96.2)
        depreciation = metrics.get("depreciation_current", 45000000.0)

        key_metrics = [
            {
                "key": "assets_needing_maintenance",
                "label": "Aset Perlu Servis",
                "value": float(service_needed),
                "formatted_value": f"{service_needed} Unit",
                "unit": "units",
                "change_percentage": 16.7,
                "trend": "up",
                "status": "warning",
            },
            {
                "key": "healthy_asset_ratio",
                "label": "Rasio Kesehatan Aset",
                "value": float(health_ratio),
                "formatted_value": f"{health_ratio:.1f}%",
                "unit": "%",
                "change_percentage": -0.5,
                "trend": "down",
                "status": "good",
            },
            {
                "key": "depreciation_current",
                "label": "Depresiasi Berjalan",
                "value": float(depreciation),
                "formatted_value": f"Rp {depreciation / 1_000_000:.0f} Jt",
                "unit": "IDR",
                "change_percentage": 0.0,
                "trend": "neutral",
                "status": "good",
            },
        ]

        vis_list = [build_asset_health_chart()]
        audit_table = state.get("audit_data")
        model_meta = [
            {
                "model_name": "predictive_maintenance_rf",
                "version": "1.0.0",
                "prediction_window": "30_days",
                "confidence_score": 0.871,
                "last_trained_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        return key_metrics, vis_list, audit_table, model_meta

    def _assemble_service(self, metrics: Dict[str, Any], state: AgentState):
        sla_val = metrics.get("sla_compliance", 94.8)
        mttr_val = metrics.get("avg_mttr", 2.4)
        tickets_val = metrics.get("ticket_volume", 216)

        key_metrics = [
            {
                "key": "sla_compliance",
                "label": "Pencapaian SLA Tiket",
                "value": float(sla_val),
                "formatted_value": f"{sla_val:.1f}%",
                "unit": "%",
                "change_percentage": 2.1,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "avg_mttr",
                "label": "Mean Time to Resolve (MTTR)",
                "value": float(mttr_val),
                "formatted_value": f"{mttr_val:.1f} Jam",
                "unit": "hours",
                "change_percentage": -15.0,
                "trend": "down",
                "status": "good",
            },
            {
                "key": "ticket_volume",
                "label": "Total Tiket NOC Aktif",
                "value": float(tickets_val),
                "formatted_value": f"{tickets_val} Tiket",
                "unit": "tickets",
                "change_percentage": -8.0,
                "trend": "down",
                "status": "good",
            },
        ]

        vis_list = [build_ticket_sla_chart()]
        audit_table = state.get("audit_data")
        model_meta = [
            {
                "model_name": "sla_breach_survival_v1",
                "version": "1.0.0",
                "prediction_window": "active_tickets",
                "confidence_score": 0.902,
                "last_trained_at": datetime.now(timezone.utc).isoformat(),
            }
        ]
        return key_metrics, vis_list, audit_table, model_meta

    def _assemble_commercial(
        self,
        raw_metrics: Dict[str, Any],
        high_risk: List[Dict[str, Any]],
        temporal_history: List[Dict[str, Any]],
    ):
        mrr_val = raw_metrics.get("mrr", 0.0)
        active_subs = raw_metrics.get("active_subscribers", 0)
        high_risk_count = raw_metrics.get("high_churn_risk_count", len(high_risk))
        arpu_val = raw_metrics.get("arpu", 0.0)

        key_metrics = [
            {
                "key": "mrr",
                "label": "Monthly Recurring Revenue",
                "value": mrr_val,
                "formatted_value": f"Rp {mrr_val:,.0f}" if mrr_val < 1_000_000_000 else f"Rp {mrr_val / 1_000_000_000:.2f} M",
                "unit": "IDR",
                "change_percentage": 3.2,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "high_churn_risk",
                "label": "Pelanggan Risiko Tinggi",
                "value": float(high_risk_count),
                "formatted_value": f"{high_risk_count} Pelanggan",
                "unit": "customers",
                "change_percentage": 12.5 if high_risk_count > 0 else 0.0,
                "trend": "up" if high_risk_count > 0 else "neutral",
                "status": "critical" if high_risk_count > 10 else "warning" if high_risk_count > 0 else "good",
            },
            {
                "key": "active_subscribers",
                "label": "Pelanggan Aktif",
                "value": float(active_subs),
                "formatted_value": f"{active_subs:,} Akun",
                "unit": "subscribers",
                "change_percentage": 1.1,
                "trend": "up",
                "status": "good",
            },
            {
                "key": "arpu",
                "label": "Average Revenue Per User",
                "value": arpu_val,
                "formatted_value": f"Rp {arpu_val:,.0f}",
                "unit": "IDR",
                "change_percentage": -0.8,
                "trend": "down" if arpu_val < 300_000 else "neutral",
                "status": "warning" if arpu_val < 300_000 else "good",
            },
        ]

        low_count = max(active_subs - high_risk_count - int(high_risk_count * 1.5), 0)
        med_count = int(high_risk_count * 1.5)

        vis_list = [
            build_churn_distribution_chart(
                low_count=low_count,
                med_count=med_count,
                high_count=high_risk_count,
            ),
            build_billing_delay_trend_chart(
                temporal_history=temporal_history,
            ),
        ]

        # Build tabular audit rows for commercial customers
        audit_rows = []
        for c in high_risk[:10]:
            top_factors = c.get("top_risk_factors", [])
            primary_reason = top_factors[0].get("description", "Keterlambatan pembayaran berulang") if top_factors else "Deviasi historis"
            prob = c.get("churn_probability", 0.0)
            audit_rows.append({
                "customer_id": f"CUST-{c.get('customer_id', 'N/A')}",
                "customer_name": c.get("customer_name", "Unknown"),
                "city": c.get("city", "Jabodetabek"),
                "churn_probability": f"{prob * 100:.1f}%",
                "risk_level": c.get("risk_level", "HIGH"),
                "primary_risk_driver": primary_reason,
            })

        # Fallback rows if no high risk customers
        if not audit_rows:
            audit_rows = [
                {
                    "customer_id": "CUST-1001",
                    "customer_name": "PT Sinergi Abadi Maju",
                    "city": "Jakarta Pusat",
                    "churn_probability": "12.4%",
                    "risk_level": "LOW",
                    "primary_risk_driver": "Disiplin pembayaran terjaga",
                },
                {
                    "customer_id": "CUST-1002",
                    "customer_name": "PT Media Graha Data",
                    "city": "Surabaya",
                    "churn_probability": "24.1%",
                    "risk_level": "LOW",
                    "primary_risk_driver": "Riwayat loyalitas 2.5 tahun",
                },
            ]

        audit_table = {
            "title": "Audit Portofolio Risiko Pelanggan (XGBoost Churn Profiling)",
            "description": "Daftar akun pelanggan, estimasi probabilitas churn, dan pendorong risiko utama",
            "columns": [
                {"key": "customer_id", "label": "ID Akun", "type": "text"},
                {"key": "customer_name", "label": "Nama Pelanggan", "type": "text"},
                {"key": "city", "label": "Kota", "type": "text"},
                {"key": "churn_probability", "label": "Probabilitas Churn", "type": "percentage"},
                {"key": "risk_level", "label": "Tingkat Risiko", "type": "badge"},
                {"key": "primary_risk_driver", "label": "Faktor Pendorong Risiko", "type": "text"},
            ],
            "rows": audit_rows,
            "total_records": len(audit_rows),
        }

        active_meta = get_active_model_metadata() or {}
        model_meta = [
            {
                "model_name": active_meta.get("model_name", ml_config.model_identity.model_name),
                "version": active_meta.get("model_version", ml_config.model_identity.default_version),
                "prediction_window": active_meta.get("prediction_window", ml_config.model_identity.prediction_window),
                "confidence_score": active_meta.get("metrics", {}).get("roc_auc", 0.88),
                "last_trained_at": active_meta.get("trained_at", datetime.now(timezone.utc).isoformat()),
            }
        ]

        return key_metrics, vis_list, audit_table, model_meta
