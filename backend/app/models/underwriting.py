"""Underwriting tables.

Mirrors ``iron_bank.underwritings`` / ``uw_details`` / ``uw_taxes`` from the
main backend. Differences for the assessment: public schema, the foreign key
to ``users`` is dropped (columns kept as plain integers), and an
``is_reference`` flag marks the analyst "answer key" a trainee is scored
against.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Underwriting(Base):
    __tablename__ = "underwritings"
    __table_args__ = (
        CheckConstraint(
            "deal_status IS NULL OR deal_status IN ("
            "'template_generated', "
            "'analyst_started', "
            "'analyst_completed', "
            "'delete_zillow', "
            "'delete_deal', "
            "'maybe', "
            "'re_forecast_revenue', "
            "'awaiting_realtor_details', "
            "'present_to_clients', "
            "'client_under_contract', "
            "'training_deal', "
            "'previously_underwritten_no_status'"
            ")",
            name="ck_underwritings_deal_status",
        ),
        CheckConstraint(
            "deal_score IS NULL OR (deal_score >= 1 AND deal_score <= 100)",
            name="ck_underwritings_deal_score",
        ),
        Index(
            "uq_underwritings_sheet_number",
            "sheet_number",
            unique=True,
            postgresql_where=text("sheet_number IS NOT NULL"),
        ),
        Index(
            "uq_underwritings_reference_zpid",
            "zpid",
            unique=True,
            postgresql_where=text("is_reference IS TRUE"),
        ),
        UniqueConstraint(
            "series_id", "version", name="uq_underwritings_series_version"
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)

    series_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    version = Column(Integer, nullable=False, default=0, server_default=text("0"))
    copied_from_id = Column(
        Integer,
        ForeignKey("underwritings.id", ondelete="SET NULL"),
        nullable=True,
    )

    zpid = Column(
        Text,
        ForeignKey("properties.zpid", ondelete="SET NULL"),
        nullable=True,
    )

    market_id = Column(
        Integer,
        ForeignKey("markets.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Kept for parity with the main backend; no FK targets here.
    analyst_id = Column(Integer, nullable=True)
    approver_id = Column(Integer, nullable=True)
    owner_id = Column(Integer, nullable=True)

    # True for the analyst-completed answer key (one per zpid); False for
    # trainee attempts.
    is_reference = Column(
        Boolean, nullable=False, default=False, server_default=text("false")
    )

    deal_status = Column(String(50), nullable=True)
    deal_added = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=True
    )
    deal_submitted = Column(DateTime(timezone=True), nullable=True)
    deal_approved = Column(DateTime(timezone=True), nullable=True)
    property_pending = Column(Boolean, default=False)
    is_automated = Column(Boolean, nullable=True)

    property_address = Column(String(255), nullable=True)
    street = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(50), nullable=True)
    days_on_market = Column(Integer, nullable=True)
    sleep_count_low = Column(Integer, nullable=True)
    sleep_count_high = Column(Integer, nullable=True)
    bedrooms = Column(Integer, nullable=True)
    bathrooms = Column(Numeric(4, 1), nullable=True)

    purchase_price = Column(Numeric(12, 2), nullable=True)
    total_oop = Column(Numeric(12, 2), nullable=True)
    prr = Column(Numeric(6, 4), nullable=True)
    budget_to_pp = Column(Numeric(6, 4), nullable=True)
    low_gross_revenue = Column(Numeric(12, 2), nullable=True)
    mid_gross_revenue = Column(Numeric(12, 2), nullable=True)
    high_gross_revenue = Column(Numeric(12, 2), nullable=True)
    l_cash_on_cash = Column(Numeric(6, 4), nullable=True)
    m_cash_on_cash = Column(Numeric(6, 4), nullable=True)
    h_cash_on_cash = Column(Numeric(6, 4), nullable=True)

    turnkey = Column(Boolean, default=False)
    furnished = Column(Boolean, default=False)
    luxury = Column(Boolean, default=False)
    tax_efficient = Column(Boolean, default=False)
    new_construction = Column(Boolean, default=False)
    existing_airbnb = Column(Boolean, default=False)
    arv = Column(Boolean, default=False)
    high_cash_on_cash = Column(Boolean, default=False)
    low_cash_on_cash = Column(Boolean, default=False)
    add_inground_pool = Column(Boolean, default=False)
    renovation_level = Column(SmallInteger, nullable=True)
    deal_complexity = Column(SmallInteger, nullable=True)
    waterfront = Column(Boolean, default=False)
    remote = Column(Boolean, default=False)
    can_support_cohost = Column(Boolean, default=False)

    market_type = Column(ARRAY(Text), nullable=True)
    execution_type = Column(String(50), nullable=True)
    seasonality = Column(ARRAY(Text), nullable=True)
    regulatory_clarity = Column(String(50), nullable=True)
    offer_competitiveness = Column(String(50), nullable=True)
    core_value_driver = Column(ARRAY(Text), nullable=True)
    cash_flow_quality = Column(String(50), nullable=True)
    view_quality = Column(String(50), nullable=True)
    pool_type = Column(String(50), nullable=True)
    primary_guest_avatar = Column(String(50), nullable=True)
    target_demographic = Column(String(50), nullable=True)

    listing_url = Column(Text, nullable=True)
    loom_vid = Column(Text, nullable=True)
    deal_pitch = Column(Text, nullable=True)
    video_walkthrough = Column(Text, nullable=True)
    survey = Column(Text, nullable=True)
    note = Column(Text, nullable=True)

    deal_score = Column(Integer, nullable=True)

    source = Column(String(50), nullable=True, server_default="adus")
    sheet_number = Column(Integer, nullable=True)

    created_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    listing = relationship("Property", back_populates="underwritings")
    market = relationship("Market", back_populates="underwritings")

    detail = relationship(
        "UnderwritingDetail",
        back_populates="underwriting",
        uselist=False,
        cascade="all, delete-orphan",
    )
    taxes = relationship(
        "UnderwritingTax",
        back_populates="underwriting",
        uselist=False,
        cascade="all, delete-orphan",
    )
    optimization_items = relationship(
        "UnderwritingOptimizationItem",
        back_populates="underwriting",
        cascade="all, delete-orphan",
        order_by=(
            "[UnderwritingOptimizationItem.sort_order, UnderwritingOptimizationItem.id]"
        ),
    )
    operating_expenses = relationship(
        "UnderwritingOperatingExpense",
        back_populates="underwriting",
        cascade="all, delete-orphan",
        order_by=(
            "[UnderwritingOperatingExpense.sort_order, UnderwritingOperatingExpense.id]"
        ),
    )
    comp_set = relationship(
        "UnderwritingCompSet",
        back_populates="underwriting",
        cascade="all, delete-orphan",
        order_by="[UnderwritingCompSet.sort_order, UnderwritingCompSet.id]",
    )
    submissions = relationship(
        "TrainingSubmission",
        back_populates="underwriting",
        foreign_keys="TrainingSubmission.underwriting_id",
        cascade="all, delete-orphan",
    )


class UnderwritingDetail(Base):
    __tablename__ = "uw_details"
    __table_args__ = (
        Index("uq_uw_details_underwriting_id", "underwriting_id", unique=True),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    underwriting_id = Column(
        Integer,
        ForeignKey("underwritings.id", ondelete="CASCADE"),
        nullable=False,
    )

    purchase_details = Column(JSONB, nullable=True)
    y1_coc_incl_tax_savings = Column(JSONB, nullable=True)
    forecasted_revenue = Column(JSONB, nullable=True)
    cleaning_cost = Column(JSONB, nullable=True)
    property_taxes = Column(JSONB, nullable=True)
    zillow_property = Column(JSONB, nullable=True)
    analyst_notes = Column(Text, nullable=True)
    construction_and_design_notes = Column(Text, nullable=True)

    underwriting = relationship("Underwriting", back_populates="detail")


class UnderwritingTax(Base):
    __tablename__ = "uw_taxes"
    __table_args__ = (
        Index("uq_uw_taxes_underwriting_id", "underwriting_id", unique=True),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    underwriting_id = Column(
        Integer,
        ForeignKey("underwritings.id", ondelete="CASCADE"),
        nullable=False,
    )

    land_assumptions_pct = Column(Numeric(6, 4), nullable=True)
    sla_multiplier_pct = Column(Numeric(6, 4), nullable=True)
    improvement_basis = Column(Numeric(12, 2), nullable=True)
    estimated_short_life_assets = Column(Numeric(12, 2), nullable=True)
    bonus_amount_pct = Column(Numeric(6, 4), nullable=True)
    tax_rate_pct = Column(Numeric(6, 4), nullable=True)
    y1_loss_from_depreciation = Column(Numeric(12, 2), nullable=True)
    tax_savings = Column(Numeric(12, 2), nullable=True)

    underwriting = relationship("Underwriting", back_populates="taxes")
