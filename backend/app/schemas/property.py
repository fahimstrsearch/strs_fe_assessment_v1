from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PropertyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zpid: str
    img_src: str | None = None
    detail_url: str | None = None
    price: str | None = None
    unformatted_price: str | None = None
    address: str | None = None
    address_street: str | None = None
    address_city: str | None = None
    address_state: str | None = None
    address_zipcode: str | None = None
    beds: int | None = None
    baths: float | None = None
    area: int | None = None
    latitude: float | None = None
    longitude: float | None = None
    home_type: str | None = None
    home_status: str | None = None
    time_on_zillow: str | None = None
    flex_text: str | None = None
    created_at: datetime | None = None


class PropertyListResult(BaseModel):
    items: list[PropertyRead]
    total: int
