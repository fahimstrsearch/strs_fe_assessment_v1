"""Market catalogue.

A market groups the properties (and their underwritings) that share one
investment thesis: regulation, seasonality and comp set all travel with the
market rather than the individual listing.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, Text, func, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.property import Property
    from app.models.underwriting import Underwriting


class Market(Base):
    __tablename__ = "markets"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    slug: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    state: Mapped[str | None] = mapped_column(String(2))
    region: Mapped[str | None] = mapped_column(String(100))
    country: Mapped[str] = mapped_column(
        String(2), nullable=False, server_default=text("'US'")
    )
    timezone: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("true")
    )
    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    properties: Mapped[list[Property]] = relationship(
        "Property", back_populates="market"
    )
    underwritings: Mapped[list[Underwriting]] = relationship(
        "Underwriting", back_populates="market"
    )
