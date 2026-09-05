import pytest
from app.agents.commercial import CommercialAgent
from app.core.session import async_session_factory


@pytest.mark.asyncio
async def test_commercial_agent_execution():
    """Verify that CommercialAgent LangGraph executes sequentially and outputs rich analytical state."""
    async with async_session_factory() as session:
        agent = CommercialAgent(session=session)
        state = await agent.run(as_of_date="2026-09-05")

        assert state["domain"] == "commercial"
        assert state["as_of_date"] == "2026-09-05"
        assert "raw_metrics" in state
        assert "mrr" in state["raw_metrics"]
        assert "active_subscribers" in state["raw_metrics"]
        assert "temporal_history" in state
        assert isinstance(state["temporal_history"], list)
        assert "anomalies" in state
        assert isinstance(state["anomalies"], list)
