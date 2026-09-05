from datetime import date
import logging
from typing import Any, Dict, List
from langgraph.graph import END, StateGraph
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import col

from app.agents.state import AgentState
from app.agents.tools.ml_tool import MLPredictionTool
from app.agents.tools.sql_tool import SafeSQLQueryTool
from app.models.dimensions import DimCustomer, DimPackage
from app.models.facts import FactBillingMonthly, FactSubscriptionSnapshot
from app.models.features import FeatureCustomerChurn

logger = logging.getLogger("erp_agents.commercial")


class CommercialAgent:
    """LangGraph analytical agent specialized in Commercial, Subscription, and Churn Risk analysis."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sql_tool = SafeSQLQueryTool(session)
        self.ml_tool = MLPredictionTool(session)
        self.graph = self._build_graph()

    def _build_graph(self):
        workflow = StateGraph(AgentState)

        # 1. Register Nodes
        workflow.add_node("fetch_metrics", self._fetch_metrics_node)
        workflow.add_node("fetch_predictions", self._fetch_predictions_node)
        workflow.add_node("analyze_temporal_deltas", self._analyze_temporal_deltas_node)
        workflow.add_node("detect_anomalies", self._detect_anomalies_node)

        # 2. Wire Edges sequentially
        workflow.set_entry_point("fetch_metrics")
        workflow.add_edge("fetch_metrics", "fetch_predictions")
        workflow.add_edge("fetch_predictions", "analyze_temporal_deltas")
        workflow.add_edge("analyze_temporal_deltas", "detect_anomalies")
        workflow.add_edge("detect_anomalies", END)

        return workflow.compile()

    async def _fetch_metrics_node(self, state: AgentState) -> Dict[str, Any]:
        """Fetch high-level commercial KPIs: MRR, Active Subscribers, ARPU."""
        # 1. Total Active Subscriptions & MRR
        q_mrr = (
            select(
                func.count(col(FactSubscriptionSnapshot.customer_key)),
                func.sum(col(FactSubscriptionSnapshot.monthly_fee)),
            )
            .where(col(FactSubscriptionSnapshot.is_active) == True)
        )
        res_mrr = await self.session.execute(q_mrr)
        row = res_mrr.fetchone()
        active_subs = row[0] or 0
        total_mrr = float(row[1] or 0.0)
        arpu = round(total_mrr / active_subs, 2) if active_subs > 0 else 0.0

        raw_metrics = {
            "mrr": total_mrr,
            "active_subscribers": active_subs,
            "arpu": arpu,
        }
        return {"raw_metrics": raw_metrics}

    async def _fetch_predictions_node(self, state: AgentState) -> Dict[str, Any]:
        """Fetch ML predictions and high-risk segment with explainability drivers."""
        high_risk = await self.ml_tool.get_high_risk_customers(limit=25, min_probability=0.50)

        # Calculate total MRR at risk
        mrr_at_risk = 0.0
        for cust in high_risk:
            # Look up monthly fee
            cid = cust["customer_id"]
            q = (
                select(FeatureCustomerChurn.monthly_fee_current)
                .where(FeatureCustomerChurn.customer_id == cid)
                .order_by(FeatureCustomerChurn.snapshot_date.desc())
                .limit(1)
            )
            fee_res = await self.session.execute(q)
            fee = fee_res.scalar() or 0.0
            cust["monthly_fee"] = float(fee)
            mrr_at_risk += float(fee)

        raw_metrics = state.get("raw_metrics", {})
        raw_metrics["high_churn_risk_count"] = len([c for c in high_risk if c.get("risk_level") == "HIGH"])
        raw_metrics["mrr_at_risk"] = mrr_at_risk

        return {
            "risk_predictions": high_risk,
            "raw_metrics": raw_metrics,
        }

    async def _analyze_temporal_deltas_node(self, state: AgentState) -> Dict[str, Any]:
        """Extract multi-snapshot temporal history to detect degradation velocity."""
        # Query billing delay trajectory for past 3 periods
        query = (
            select(
                FactBillingMonthly.invoice_period,
                func.count(FactBillingMonthly.customer_key),
                func.avg(FactBillingMonthly.days_late),
                func.sum(FactBillingMonthly.invoiced_amount),
            )
            .group_by(FactBillingMonthly.invoice_period)
            .order_by(FactBillingMonthly.invoice_period.desc())
            .limit(4)
        )
        res = await self.session.execute(query)
        rows = res.fetchall()

        history = []
        for r in reversed(rows):
            history.append({
                "period": str(r[0]),
                "total_invoices": r[1],
                "avg_days_late": round(float(r[2] or 0.0), 1),
                "total_invoiced": float(r[3] or 0.0),
            })

        return {"temporal_history": history}

    async def _detect_anomalies_node(self, state: AgentState) -> Dict[str, Any]:
        """Identify package concentrations, critical delays, and operational friction points."""
        high_risk = state.get("risk_predictions", [])
        anomalies = []

        # 1. Detect severe chronic late payments
        chronic_late = [
            c for c in high_risk
            if any(f.get("feature") == "late_payment_count_3m" and (f.get("value") or 0) >= 2 for f in c.get("top_risk_factors", []))
        ]
        if chronic_late:
            anomalies.append({
                "type": "CHRONIC_PAYMENT_DEFAULT",
                "severity": "CRITICAL",
                "affected_count": len(chronic_late),
                "description": f"{len(chronic_late)} pelanggan mengalami keterlambatan bayar berulang (>= 2 kali dalam 3 bulan terakhir).",
            })

        # 2. Detect worsening payment trend acceleration
        worsening_trend = [
            c for c in high_risk
            if any(f.get("feature") == "payment_status_trend" and f.get("value") == "WORSENING" for f in c.get("top_risk_factors", []))
        ]
        if worsening_trend:
            anomalies.append({
                "type": "PAYMENT_ACCELERATION_DEGRADATION",
                "severity": "WARNING",
                "affected_count": len(worsening_trend),
                "description": f"{len(worsening_trend)} pelanggan menunjukkan tren kedisiplinan pembayaran yang memburuk.",
            })

        return {"anomalies": anomalies}

    async def run(self, as_of_date: Optional[str] = None) -> AgentState:
        """Execute the LangGraph workflow and return compiled agent state."""
        target_date = as_of_date or str(date.today())
        initial_state: AgentState = {
            "domain": "commercial",
            "as_of_date": target_date,
            "raw_metrics": {},
            "temporal_history": [],
            "risk_predictions": [],
            "anomalies": [],
            "synthesized_narratives": [],
            "chart_specs": [],
            "errors": [],
        }

        final_state = await self.graph.ainvoke(initial_state)
        return final_state
