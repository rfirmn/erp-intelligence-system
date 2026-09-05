from datetime import datetime
from typing import ClassVar, Optional
from sqlmodel import Field, SQLModel

from app.core.datetime_utils import utc_now


class DimUser(SQLModel, table=True):
    """User account entity for single-tier Dashboard Intelligence login access."""
    __tablename__: ClassVar[str] = "dim_user"  # type: ignore
    __table_args__ = {"schema": "feature_store"}

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(..., unique=True, index=True, max_length=100)
    email: Optional[str] = Field(default=None, unique=True, index=True, max_length=150)
    hashed_password: str = Field(..., max_length=255)
    full_name: Optional[str] = Field(default=None, max_length=150)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=utc_now)
    last_login_at: Optional[datetime] = Field(default=None)
