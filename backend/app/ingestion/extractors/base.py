from abc import ABC, abstractmethod
from datetime import datetime
import logging
from typing import Any, Dict, List, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.extractors.erp_client import erp_connector
from app.ingestion.observability import get_last_successful_watermark

logger = logging.getLogger("erp_ingestion.extractors")


class BaseExtractor(ABC):
    """Abstract base extractor handling watermark windows and source execution."""

    def __init__(self, source_table: str):
        self.source_table = source_table

    async def get_effective_since(self, session: AsyncSession, override_since: Optional[datetime] = None) -> Optional[datetime]:
        """Determine starting watermark: override takes precedence, otherwise latest successful batch."""
        if override_since:
            return override_since
        return await get_last_successful_watermark(session, self.source_table)

    @abstractmethod
    async def extract(
        self,
        since: Optional[datetime],
        until: datetime,
        limit: int = 5000,
    ) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
        """Extract incremental records from ERP source."""
        pass
