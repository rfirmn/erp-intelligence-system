import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.ml.config import ml_config
from app.ml.inference.churn_predictor import ChurnInferenceService

logger = logging.getLogger("erp_agents.tools.ml")


class MLPredictionTool:
    """Tool for analytical agents to query customer churn risk and SHAP explainability drivers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_high_risk_customers(
        self,
        limit: Optional[int] = None,
        min_probability: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """Retrieve highest risk customers with associated TreeSHAP drivers."""
        resolved_limit = limit if limit is not None else settings.AGENT_HIGH_RISK_LIMIT
        resolved_min_prob = (
            min_probability if min_probability is not None else ml_config.risk_thresholds.medium_risk
        )
        return await ChurnInferenceService.get_high_risk_customers(
            session=self.session,
            limit=resolved_limit,
            min_probability=resolved_min_prob,
        )

    async def get_customer_risk_detail(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve full predictive profile for an individual customer."""
        return await ChurnInferenceService.get_customer_prediction(
            session=self.session,
            customer_id=customer_id,
        )
