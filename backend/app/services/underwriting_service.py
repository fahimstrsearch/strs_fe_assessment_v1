"""Start, save and submit trainee underwritings."""

from datetime import UTC, datetime

from app.core.logger import logger
from app.models import Underwriting
from app.repositories.property_repository import PropertyRepository
from app.repositories.underwriting_repository import UnderwritingRepository
from app.schemas.underwriting import (
    ForecastedRevenueInput,
    OperatingExpenseInput,
    OptimizationItemInput,
    PurchaseDetailsInput,
    SaveUnderwritingPayload,
    UnderwritingRead,
    UnderwritingTaxInput,
)
from app.services.underwriting_calculator import (
    CalculatedUnderwriting,
    UnderwritingCalculator,
)

TRAINING_STATUS = "training_deal"
STARTED_STATUS = "analyst_started"
COMPLETED_STATUS = "analyst_completed"


class IncompleteUnderwritingError(ValueError):
    """Raised on submit when a required section is missing."""


class UnderwritingService:
    def __init__(
        self,
        repository: UnderwritingRepository,
        property_repository: PropertyRepository,
        calculator: UnderwritingCalculator | None = None,
    ):
        self.repository = repository
        self.property_repository = property_repository
        self.calculator = calculator or UnderwritingCalculator()

    async def start(self, zpid: str) -> UnderwritingRead:
        prop = await self.property_repository.get(zpid)
        if prop is None:
            raise LookupError(f"Property {zpid} not found")

        underwriting = Underwriting(
            zpid=prop.zpid,
            is_reference=False,
            deal_status=STARTED_STATUS,
            source="training",
            property_address=prop.address,
            street=prop.address_street,
            city=prop.address_city,
            state=prop.address_state,
            bedrooms=prop.beds,
            bathrooms=prop.baths,
            listing_url=prop.detail_url,
            purchase_price=_to_decimal(prop.unformatted_price),
        )
        self.repository.ensure_detail(underwriting).zillow_property = {
            "zpid": prop.zpid,
            "address": prop.address,
            "price": prop.price,
            "beds": prop.beds,
            "baths": prop.baths,
            "area": prop.area,
            "home_type": prop.home_type,
            "img_src": prop.img_src,
            "detail_url": prop.detail_url,
        }
        await self.repository.create(underwriting)
        saved = await self.repository.commit_and_refresh(underwriting)
        logger.info("underwriting.started", underwriting_id=saved.id, zpid=zpid)
        return UnderwritingRead.model_validate(saved)

    async def get(self, underwriting_id: int) -> UnderwritingRead:
        row = await self._get_editable(underwriting_id, allow_reference=True)
        return UnderwritingRead.model_validate(row)

    async def save(
        self, underwriting_id: int, payload: SaveUnderwritingPayload
    ) -> UnderwritingRead:
        row = await self._get_editable(underwriting_id)
        self._apply_payload(row, payload)
        # Derive what we can so the form can show live numbers, but never
        # fail a draft save because a section is still empty.
        try:
            self._recalculate(row)
        except IncompleteUnderwritingError:
            pass
        saved = await self.repository.commit_and_refresh(row)
        return UnderwritingRead.model_validate(saved)

    async def submit(
        self, underwriting_id: int, payload: SaveUnderwritingPayload | None = None
    ) -> Underwriting:
        """Persist the final numbers and mark the deal submitted.

        Returns the ORM row (with children) so the caller can score it.
        """
        row = await self._get_editable(underwriting_id)
        if payload is not None:
            self._apply_payload(row, payload)
        self._recalculate(row)
        row.deal_status = COMPLETED_STATUS
        row.deal_submitted = datetime.now(UTC)
        return await self.repository.commit_and_refresh(row)

    # ------------------------------------------------------------- helpers --

    async def _get_editable(
        self, underwriting_id: int, *, allow_reference: bool = False
    ) -> Underwriting:
        row = await self.repository.get_by_id(underwriting_id)
        if row is None:
            raise LookupError(f"Underwriting {underwriting_id} not found")
        if row.is_reference and not allow_reference:
            raise PermissionError("Reference underwritings are read-only")
        return row

    def _apply_payload(
        self, row: Underwriting, payload: SaveUnderwritingPayload
    ) -> None:
        data = payload.model_dump(exclude_unset=True)
        detail = self.repository.ensure_detail(row)

        for field in (
            "bedrooms",
            "bathrooms",
            "sleep_count_low",
            "sleep_count_high",
            "deal_pitch",
            "note",
        ):
            if field in data:
                setattr(row, field, data[field])
        if "analyst_notes" in data:
            detail.analyst_notes = data["analyst_notes"]
        if "tags" in data and data["tags"] is not None:
            for field, value in data["tags"].items():
                if value is not None:
                    setattr(row, field, value)

        if "purchase_details" in data:
            detail.purchase_details = _jsonable(data["purchase_details"])
            if data["purchase_details"]:
                row.purchase_price = data["purchase_details"]["purchase_price"]
        if "forecasted_revenue" in data:
            detail.forecasted_revenue = _jsonable(data["forecasted_revenue"])
        if "taxes" in data:
            taxes = self.repository.ensure_taxes(row)
            for field, value in (data["taxes"] or {}).items():
                setattr(taxes, field, value)
        if "optimization_items" in data:
            self.repository.replace_optimization_items(
                row, data["optimization_items"] or []
            )
        if "operating_expenses" in data:
            self.repository.replace_operating_expenses(
                row, data["operating_expenses"] or []
            )
        if "comp_set" in data:
            self.repository.replace_comp_set(row, data["comp_set"] or [])

    def _recalculate(self, row: Underwriting) -> CalculatedUnderwriting:
        detail = row.detail
        missing = [
            name
            for name, present in (
                ("purchase_details", bool(detail and detail.purchase_details)),
                ("forecasted_revenue", bool(detail and detail.forecasted_revenue)),
                (
                    "taxes",
                    row.taxes is not None
                    and row.taxes.land_assumptions_pct is not None,
                ),
            )
            if not present
        ]
        if missing:
            raise IncompleteUnderwritingError(
                f"Missing required sections: {', '.join(missing)}"
            )

        calc = self.calculator.calculate(
            purchase_details=PurchaseDetailsInput.model_validate(
                detail.purchase_details
            ),
            forecasted_revenue=ForecastedRevenueInput.model_validate(
                detail.forecasted_revenue
            ),
            taxes=UnderwritingTaxInput(
                land_assumptions_pct=row.taxes.land_assumptions_pct,
                sla_multiplier_pct=row.taxes.sla_multiplier_pct,
                bonus_amount_pct=row.taxes.bonus_amount_pct,
                tax_rate_pct=row.taxes.tax_rate_pct,
            ),
            optimization_items=[
                OptimizationItemInput(total_price=i.total_price)
                for i in row.optimization_items
            ],
            operating_expenses=[
                OperatingExpenseInput(monthly_amount=e.monthly_amount)
                for e in row.operating_expenses
            ],
        )

        detail.purchase_details = _jsonable(calc.purchase_details)
        detail.forecasted_revenue = _jsonable(calc.forecasted_revenue)
        detail.y1_coc_incl_tax_savings = _jsonable(calc.y1_coc_incl_tax_savings)
        for field in (
            "improvement_basis",
            "estimated_short_life_assets",
            "y1_loss_from_depreciation",
            "tax_savings",
        ):
            setattr(row.taxes, field, calc.taxes[field])
        for field in (
            "purchase_price",
            "total_oop",
            "prr",
            "budget_to_pp",
            "low_gross_revenue",
            "mid_gross_revenue",
            "high_gross_revenue",
            "l_cash_on_cash",
            "m_cash_on_cash",
            "h_cash_on_cash",
        ):
            setattr(
                row,
                field,
                calc.purchase_details["purchase_price"]
                if field == "purchase_price"
                else getattr(calc, field),
            )
        return calc


def _to_decimal(value):
    from decimal import Decimal, InvalidOperation

    if value in (None, ""):
        return None
    try:
        return Decimal(str(value))
    except InvalidOperation:
        return None


def _jsonable(value):
    """Decimals -> str so the dict can be stored in JSONB."""
    from decimal import Decimal

    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value
