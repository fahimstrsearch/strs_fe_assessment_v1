"""Training property catalogue.

Mirrors ``zillow.scheduled_listings`` from the main backend, minus the preset
foreign key, and lives in the public schema because this is an assessment.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    Text,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.market import Market
    from app.models.underwriting import Underwriting


class Property(Base):
    __tablename__ = "properties"
    __table_args__ = (Index("ix_properties_market_id", "market_id"),)

    zpid: Mapped[str] = mapped_column(Text, primary_key=True)
    img_src: Mapped[str | None] = mapped_column(Text)
    detail_url: Mapped[str | None] = mapped_column(Text)
    price: Mapped[str | None] = mapped_column(Text)
    unformatted_price: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    address_street: Mapped[str | None] = mapped_column(Text)
    address_city: Mapped[str | None] = mapped_column(Text)
    address_state: Mapped[str | None] = mapped_column(Text)
    address_zipcode: Mapped[str | None] = mapped_column(Text)
    beds: Mapped[int | None] = mapped_column(Integer)
    baths: Mapped[float | None] = mapped_column(Float)
    area: Mapped[int | None] = mapped_column(Integer)
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    home_type: Mapped[str | None] = mapped_column(Text)
    home_status: Mapped[str | None] = mapped_column(Text)
    time_on_zillow: Mapped[str | None] = mapped_column(Text)
    flex_text: Mapped[str | None] = mapped_column(Text)
    keep_updated: Mapped[bool | None] = mapped_column(
        Boolean, server_default=text("true")
    )
    remove_listing: Mapped[bool | None] = mapped_column(
        Boolean, server_default=text("false")
    )
    last_seen: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=text("CURRENT_TIMESTAMP")
    )
    passes_preset_filters: Mapped[bool | None] = mapped_column(Boolean)

    market_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("markets.id", ondelete="SET NULL")
    )

    market: Mapped[Market | None] = relationship(
        "Market", back_populates="properties", lazy="joined"
    )
    underwritings: Mapped[list[Underwriting]] = relationship(
        "Underwriting", back_populates="listing"
    )
