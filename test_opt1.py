
from typing import Any, Optional
from sqlalchemy.orm import declared_attr
from sqlmodel import Field, SQLModel

class StgStock(SQLModel, table=True):
    @declared_attr
    def __tablename__(cls) -> Any:
        return "stg_stock"
    __table_args__ = {"schema": "staging"}

    id: Optional[int] = Field(default=None, primary_key=True)
