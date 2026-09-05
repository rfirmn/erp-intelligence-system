import logging
from typing import Any, Dict, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.ml.inference.churn_predictor import ChurnInferenceService

logger = logging.getLogger("erp_agents.tools.ml")


class MLPredictionTool:
    """Tool for analytical agents to query customer churn risk and SHAP explainability drivers."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_high_risk_customers(
        self,
        limit: int = 15,
        min_probability: float = 0.60,
    ) -> List[Dict[str, Any]]:
        """Retrieve highest risk customers with associated TreeSHAP drivers."""
        return await ChurnInferenceService.get_high_risk_customers(
            session=self.session,
            limit=limit,
            min_probability=min_probability,
        )

    async def get_customer_risk_detail(self, customer_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve full predictive profile for an individual customer."""
        return await ChurnInferenceService.get_customer_prediction(
            session=self.session,
            customer_id=customer_id,
        )
