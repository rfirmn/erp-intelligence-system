from datetime import datetime, timezone
from typing import Optional


def utc_now() -> datetime:
    """Return naive UTC datetime for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def to_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Convert an offset-aware datetime to naive UTC datetime, or return None."""
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
