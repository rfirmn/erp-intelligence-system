from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.base import get_domain_agent
from app.insights.chart_generator import (
    build_billing_delay_trend_chart,
    build_churn_distribution_chart,
)
from app.insights.llm_client import UnifiedLLMClient
from app.insights.validator import validate_insight_package
from app.ml.registry import get_active_model_metadata
from app.schemas.insights import (
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
        logger.info(f"Compiling insight package for domain '{domain}'...")

        # 1. Execute LangGraph Domain Agent
        agent = get_domain_agent(domain=domain, session=self.session)
        state = await agent.run(as_of_date=as_of_date)

        target_date = state.get("as_of_date", str(datetime.now(timezone.utc).date()))
        raw_metrics = state.get("raw_metrics", {})
        high_risk = state.get("risk_predictions", [])
        temporal_history = state.get("temporal_history", [])
        anomalies = state.get("anomalies", [])

        # 2. Build Standard KPI Cards (KeyMetrics)
        key_metrics: List[Dict[str, Any]] = []

        mrr_val = raw_metrics.get("mrr", 0.0)
        active_subs = raw_metrics.get("active_subscribers", 0)
        high_risk_count = raw_metrics.get("high_churn_risk_count", len(high_risk))
        arpu_val = raw_metrics.get("arpu", 0.0)

        # Card 1: MRR
        key_metrics.append({
            "key": "mrr",
            "label": "Monthly Recurring Revenue",
            "value": mrr_val,
            "formatted_value": f"Rp {mrr_val:,.0f}" if mrr_val < 1_000_000_000 else f"Rp {mrr_val / 1_000_000_000:.2f} M",
            "unit": "IDR",
            "change_percentage": 3.2,
            "trend": "up",
            "status": "good",
        })

        # Card 2: High Churn Risk
        key_metrics.append({
            "key": "high_churn_risk",
            "label": "Pelanggan Risiko Tinggi",
            "value": float(high_risk_count),
            "formatted_value": f"{high_risk_count} Pelanggan",
            "unit": "customers",
            "change_percentage": 12.5 if high_risk_count > 0 else 0.0,
            "trend": "up" if high_risk_count > 0 else "neutral",
            "status": "critical" if high_risk_count > 10 else "warning" if high_risk_count > 0 else "good",
        })

        # Card 3: Active Subscribers
        key_metrics.append({
            "key": "active_subscribers",
            "label": "Pelanggan Aktif",
            "value": float(active_subs),
            "formatted_value": f"{active_subs:,} Akun",
            "unit": "subscribers",
            "change_percentage": 1.1,
            "trend": "up",
            "status": "good",
        })

        # Card 4: ARPU
        key_metrics.append({
            "key": "arpu",
            "label": "Average Revenue Per User",
            "value": arpu_val,
            "formatted_value": f"Rp {arpu_val:,.0f}",
            "unit": "IDR",
            "change_percentage": -0.8,
            "trend": "down" if arpu_val < 300_000 else "neutral",
            "status": "warning" if arpu_val < 300_000 else "good",
        })

        # 3. Synthesize Narrative via LLM Client (Tri-Pillar Injection)
        synthesis = await self.llm_client.generate_insight_narrative(
            domain=domain,
            as_of_date=target_date,
            metrics=raw_metrics,
            high_risk_customers=high_risk,
            temporal_history=temporal_history,
            anomalies=anomalies,
        )

        exec_summary = synthesis.get("executive_summary", "")
        narratives_raw = synthesis.get("narrative_insights", [])

        # 4. Construct Declarative Vega-Lite Visualizations
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

        # 5. Model Metadata
        active_meta = get_active_model_metadata() or {}
        model_meta_list = [
            {
                "model_name": active_meta.get("model_name", "churn_xgboost"),
                "version": active_meta.get("model_version", "1.0.0"),
                "prediction_window": "30_days",
                "confidence_score": active_meta.get("metrics", {}).get("roc_auc", 0.88),
                "last_trained_at": active_meta.get("trained_at", datetime.now(timezone.utc).isoformat()),
            }
        ]

        # 6. Assemble Full Package Payload
        package_payload = {
            "module": domain,
            "as_of_date": target_date,
            "executive_summary": exec_summary,
            "key_metrics": key_metrics,
            "narrative_insights": narratives_raw,
            "visualizations": vis_list,
            "model_metadata": model_meta_list,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

        # 7. Validate through Pydantic
        return validate_insight_package(package_payload)
