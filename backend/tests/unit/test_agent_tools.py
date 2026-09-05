import pytest
from app.agents.tools.sql_tool import SafeSQLQueryTool


def test_safe_sql_tool_validation():
    """Verify that SafeSQLQueryTool blocks mutating queries and accepts valid analytical queries."""
    tool = SafeSQLQueryTool(session=None)

    # Valid queries
    tool.validate_query("SELECT * FROM feature_store.dim_customer WHERE is_current = true")
    tool.validate_query("WITH cte AS (SELECT customer_id FROM feature_store.feature_customer_churn) SELECT * FROM cte")

    # Forbidden mutations
    with pytest.raises(PermissionError, match="Hanya query SELECT atau WITH"):
        tool.validate_query("INSERT INTO feature_store.dim_customer VALUES (1)")

    with pytest.raises(PermissionError, match="terdeteksi instruksi mutasi data"):
        tool.validate_query("SELECT * FROM dim_customer; DELETE FROM dim_customer;")

    with pytest.raises(PermissionError, match="terdeteksi instruksi mutasi data"):
        tool.validate_query("SELECT * FROM dim_customer; DROP TABLE feature_store.dim_customer;")

    with pytest.raises(PermissionError, match="Hanya query SELECT atau WITH"):
        tool.validate_query("DROP TABLE feature_store.dim_customer")
