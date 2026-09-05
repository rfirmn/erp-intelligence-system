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
            # Provide baseline structured KPI cards depending on domain
            kpis = {
                "finance": {"net_cashflow": 320000000.0, "ar_aging_60_ratio": 0.084},
                "inventory": {"stockout_runway_days": 18.0, "critical_items_count": 3},
                "procurement": {"avg_vendor_delay_days": 4.2, "po_fulfillment_rate": 0.94},
                "asset": {"depreciation_current": 45000000.0, "cpe_defect_rate": 0.021},
                "service": {"sla_compliance_rate": 0.978, "avg_mttr_hours": 3.4},
                "overview": {"health_score": 88.5, "cross_module_critical_alerts": 2},
            }
            return {"raw_metrics": kpis.get(self.domain, {})}

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
            "errors": [],
        }
        return cast(AgentState, await self.graph.ainvoke(initial_state))


def get_domain_agent(domain: str, session: AsyncSession) -> Union[CommercialAgent, GenericDomainAgent]:
    """Factory helper to obtain domain-specialized LangGraph agent."""
    norm = domain.lower()
    if norm == "commercial":
        return CommercialAgent(session)
    return GenericDomainAgent(norm, session)
