import logging
import re
from typing import Any, Dict, List
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("erp_agents.tools.sql")

FORBIDDEN_KEYWORDS = [
    r"\bINSERT\b",
    r"\bUPDATE\b",
    r"\bDELETE\b",
    r"\bDROP\b",
    r"\bALTER\b",
    r"\bTRUNCATE\b",
    r"\bGRANT\b",
    r"\bREVOKE\b",
    r"\bEXEC\b",
    r"\bCREATE\b",
]


class SafeSQLQueryTool:
    """Read-only SQL executor restricted to analytical querying on feature_store schema."""

    def __init__(self, session: AsyncSession, max_rows: int = 100):
        self.session = session
        self.max_rows = max_rows

    def validate_query(self, query: str) -> None:
        """Validate that the query is strictly a read-only SELECT statement."""
        normalized = query.strip()
        if not (normalized.upper().startswith("SELECT") or normalized.upper().startswith("WITH")):
            raise PermissionError("Hanya query SELECT atau WITH (CTE) yang diizinkan untuk dieksekusi oleh agen.")

        for kw in FORBIDDEN_KEYWORDS:
            if re.search(kw, normalized, re.IGNORECASE):
                raise PermissionError(f"Query ditolak: terdeteksi instruksi mutasi data yang dilarang ({kw.strip(r'\b')}).")

    async def execute(self, query: str, params: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """Execute validated query safely and return rows as list of dicts."""
        self.validate_query(query)

        # Enforce row limit if not already present
        clean_q = query.strip().rstrip(";")
        if "LIMIT" not in clean_q.upper():
            clean_q += f" LIMIT {self.max_rows}"

        try:
            result = await self.session.execute(text(clean_q), params or {})
            rows = result.fetchall()
            if not rows:
                return []
            return [dict(row._mapping) for row in rows]
        except Exception as e:
            logger.error(f"SafeSQLQueryTool execution error: {e}")
            raise
