from datetime import datetime
from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field

FractionalPercentage = Annotated[Decimal, Field(ge=0, le=1)]


# ---------------------------------------------------------------- inputs ----


class PurchaseDetailsInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    purchase_price: Decimal = Field(gt=0)
    down_payment_pct: FractionalPercentage
    interest_rate: FractionalPercentage
    mortgage_years: int = Field(gt=0)
    closing_costs_pct: FractionalPercentage


class ForecastedRevenueScenarioInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    forecasted_revenue: Decimal = Field(ge=0)


class ForecastedRevenueScenariosInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    low: ForecastedRevenueScenarioInput
    mid: ForecastedRevenueScenarioInput
    high: ForecastedRevenueScenarioInput


class ForecastedRevenueInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    co_hosting_fee_pct: FractionalPercentage = Decimal("0")
    annual_re_appreciation_pct: FractionalPercentage = Decimal("0")
    scenarios: ForecastedRevenueScenariosInput


class UnderwritingTaxInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    land_assumptions_pct: FractionalPercentage
    sla_multiplier_pct: FractionalPercentage
    bonus_amount_pct: FractionalPercentage
    tax_rate_pct: FractionalPercentage


class OptimizationItemInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: str | None = None
    total_price: Decimal | None = None
    metric: str | None = None
    base_price: Decimal | None = None
    spec: str | None = None
    tier: str | None = None
    notes: str | None = None


class OperatingExpenseInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    expense_name: str | None = None
    monthly_amount: Decimal | None = None


class CompSetInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listing_url: str | None = None
    revenue: Decimal | None = None
    bedrooms: int | None = None
    sleeps: int | None = None
    is_favourite: bool = False
    has_pool: bool | None = None
    has_hot_tub: bool | None = None
    has_sauna: bool | None = None
    has_mini_golf: bool | None = None
    has_game_room: bool | None = None
    has_pickleball: bool | None = None
    has_movie_theater: bool | None = None
    has_playground: bool | None = None
    has_waterfront: bool | None = None


class DealTagsInput(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turnkey: bool | None = None
    furnished: bool | None = None
    luxury: bool | None = None
    tax_efficient: bool | None = None
    new_construction: bool | None = None
    existing_airbnb: bool | None = None
    arv: bool | None = None
    high_cash_on_cash: bool | None = None
    low_cash_on_cash: bool | None = None
    add_inground_pool: bool | None = None
    waterfront: bool | None = None
    remote: bool | None = None
    can_support_cohost: bool | None = None
    renovation_level: int | None = Field(default=None, ge=1, le=5)
    deal_complexity: int | None = Field(default=None, ge=1, le=5)


class StartUnderwritingPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zpid: str


class SaveUnderwritingPayload(BaseModel):
    """Draft save. Every section is optional so the form can save partially."""

    model_config = ConfigDict(extra="forbid")

    bedrooms: int | None = None
    bathrooms: Decimal | None = None
    sleep_count_low: int | None = None
    sleep_count_high: int | None = None
    purchase_details: PurchaseDetailsInput | None = None
    forecasted_revenue: ForecastedRevenueInput | None = None
    taxes: UnderwritingTaxInput | None = None
    optimization_items: list[OptimizationItemInput] | None = None
    operating_expenses: list[OperatingExpenseInput] | None = None
    comp_set: list[CompSetInput] | None = None
    tags: DealTagsInput | None = None
    deal_pitch: str | None = None
    note: str | None = None
    analyst_notes: str | None = None


# ---------------------------------------------------------------- outputs ---


class OptimizationItemRead(OptimizationItemInput):
    model_config = ConfigDict(from_attributes=True)

    id: int


class OperatingExpenseRead(OperatingExpenseInput):
    model_config = ConfigDict(from_attributes=True)

    id: int


class CompSetRead(CompSetInput):
    model_config = ConfigDict(from_attributes=True)

    id: int


class UnderwritingTaxRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    land_assumptions_pct: Decimal | None = None
    sla_multiplier_pct: Decimal | None = None
    improvement_basis: Decimal | None = None
    estimated_short_life_assets: Decimal | None = None
    bonus_amount_pct: Decimal | None = None
    tax_rate_pct: Decimal | None = None
    y1_loss_from_depreciation: Decimal | None = None
    tax_savings: Decimal | None = None


class UnderwritingDetailRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    purchase_details: dict[str, Any] | None = None
    y1_coc_incl_tax_savings: dict[str, Any] | None = None
    forecasted_revenue: dict[str, Any] | None = None
    zillow_property: dict[str, Any] | None = None
    analyst_notes: str | None = None


class UnderwritingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    zpid: str | None
    is_reference: bool
    deal_status: str | None
    deal_submitted: datetime | None
    property_address: str | None
    street: str | None
    city: str | None
    state: str | None
    bedrooms: int | None
    bathrooms: Decimal | None
    sleep_count_low: int | None
    sleep_count_high: int | None
    purchase_price: Decimal | None
    total_oop: Decimal | None
    prr: Decimal | None
    budget_to_pp: Decimal | None
    low_gross_revenue: Decimal | None
    mid_gross_revenue: Decimal | None
    high_gross_revenue: Decimal | None
    l_cash_on_cash: Decimal | None
    m_cash_on_cash: Decimal | None
    h_cash_on_cash: Decimal | None
    optimization_total: Decimal | None
    operating_expense_total: Decimal | None
    turnkey: bool | None
    furnished: bool | None
    luxury: bool | None
    tax_efficient: bool | None
    new_construction: bool | None
    existing_airbnb: bool | None
    arv: bool | None
    high_cash_on_cash: bool | None
    low_cash_on_cash: bool | None
    add_inground_pool: bool | None
    waterfront: bool | None
    remote: bool | None
    can_support_cohost: bool | None
    renovation_level: int | None
    deal_complexity: int | None
    listing_url: str | None
    deal_pitch: str | None
    note: str | None
    created_at: datetime | None
    updated_at: datetime | None
    detail: UnderwritingDetailRead | None = None
    taxes: UnderwritingTaxRead | None = None
    optimization_items: list[OptimizationItemRead] = []
    operating_expenses: list[OperatingExpenseRead] = []
    comp_set: list[CompSetRead] = []
