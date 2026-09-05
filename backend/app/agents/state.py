from typing import Any, Dict, List, Optional
from typing_extensions import TypedDict


class AgentState(TypedDict, total=False):
    """LangGraph State representation that flows across analytical agent nodes."""
    domain: str
    as_of_date: str
    raw_metrics: Dict[str, Any]
    temporal_history: List[Dict[str, Any]]
    risk_predictions: List[Dict[str, Any]]
    anomalies: List[Dict[str, Any]]
    synthesized_narratives: List[Dict[str, Any]]
    chart_specs: List[Dict[str, Any]]
    audit_data: Dict[str, Any]
    errors: List[str]
