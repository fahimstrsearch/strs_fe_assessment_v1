from datetime import datetime

from pydantic import BaseModel, ConfigDict


class MarketRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    state: str | None = None
    region: str | None = None
    country: str
    timezone: str | None = None
    description: str | None = None
    is_active: bool
    property_count: int = 0
    created_at: datetime | None = None


class MarketSummary(BaseModel):
    """Inlined on a property so a list response needs no second call."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    state: str | None = None


class MarketListResult(BaseModel):
    items: list[MarketRead]
    total: int
