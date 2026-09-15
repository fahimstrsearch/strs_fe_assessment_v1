"""Pure underwriting maths, ported from the main backend's calculator.

No I/O. Given the trainee's inputs it derives every number stored on the
``underwritings`` row (total OOP, PRR, cash-on-cash per scenario, ...).
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.schemas.underwriting import (
    ForecastedRevenueInput,
    OperatingExpenseInput,
    OptimizationItemInput,
    PurchaseDetailsInput,
    UnderwritingTaxInput,
)

_MONEY_QUANT = Decimal("0.01")
_PERCENT_QUANT = Decimal("0.0001")
_MONTHS_IN_YEAR = Decimal("12")
_OPEX_MULTIPLIERS = {
    "low": Decimal("0.96"),
    "mid": Decimal("1"),
    "high": Decimal("1.04"),
}


def money(value: Decimal) -> Decimal:
    return value.quantize(_MONEY_QUANT, rounding=ROUND_HALF_UP)


def percentage(value: Decimal) -> Decimal:
    return value.quantize(_PERCENT_QUANT, rounding=ROUND_HALF_UP)


@dataclass
class CalculatedUnderwriting:
    purchase_details: dict
    forecasted_revenue: dict
    taxes: dict
    y1_coc_incl_tax_savings: dict
    optimization_total: Decimal
    operating_expense_total: Decimal
    total_oop: Decimal
    prr: Decimal
    budget_to_pp: Decimal
    low_gross_revenue: Decimal
    mid_gross_revenue: Decimal
    high_gross_revenue: Decimal
    l_cash_on_cash: Decimal
    m_cash_on_cash: Decimal
    h_cash_on_cash: Decimal


class UnderwritingCalculator:
    def calculate(
        self,
        *,
        purchase_details: PurchaseDetailsInput,
        forecasted_revenue: ForecastedRevenueInput,
        taxes: UnderwritingTaxInput,
        optimization_items: list[OptimizationItemInput],
        operating_expenses: list[OperatingExpenseInput],
    ) -> CalculatedUnderwriting:
        pd = self.calculate_purchase_details(purchase_details)
        optimization_total = sum(
            (item.total_price or Decimal("0") for item in optimization_items),
            Decimal("0"),
        )
        opex_total = sum(
            (e.monthly_amount or Decimal("0") for e in operating_expenses),
            Decimal("0"),
        )
        total_oop = money(
            pd["down_payment_amount"] + pd["closing_costs_amount"] + optimization_total
        )
        if total_oop <= 0:
            raise ValueError("total out-of-pocket must be positive")

        debt_service_annual = self.annual_debt_service(pd)
        principal_pay_down = self.year_one_principal_pay_down(pd)
        annual_re_appreciation = (
            pd["purchase_price"] * forecasted_revenue.annual_re_appreciation_pct
        )

        scenarios: dict[str, dict] = {}
        for name, multiplier in _OPEX_MULTIPLIERS.items():
            revenue = getattr(forecasted_revenue.scenarios, name).forecasted_revenue
            opex_annual = opex_total * _MONTHS_IN_YEAR * multiplier
            co_hosting_fee = revenue * forecasted_revenue.co_hosting_fee_pct
            noi = revenue - opex_annual - co_hosting_fee
            free_cash_flow = noi - debt_service_annual
            total_return_pct = (
                free_cash_flow + principal_pay_down + annual_re_appreciation
            ) / total_oop
            scenarios[name] = {
                "forecasted_revenue": money(revenue),
                "operating_expenses_annual": money(opex_annual),
                "co_hosting_fee": money(co_hosting_fee),
                "net_operating_income": money(noi),
                "debt_service_annual": money(debt_service_annual),
                "annual_free_cash_flow": money(free_cash_flow),
                "principal_pay_down": money(principal_pay_down),
                "annual_re_appreciation": money(annual_re_appreciation),
                "annual_total_re_return_pct": percentage(total_return_pct),
                "cash_on_cash_pct": percentage(free_cash_flow / total_oop),
            }

        tax = self.calculate_taxes(taxes, pd["purchase_price"], optimization_total)
        y1_coc = {
            f"{name}_pct": percentage(
                (
                    s["net_operating_income"]
                    - s["debt_service_annual"]
                    + tax["tax_savings"]
                )
                / total_oop
            )
            for name, s in scenarios.items()
        }

        mid_revenue = scenarios["mid"]["forecasted_revenue"]
        return CalculatedUnderwriting(
            purchase_details=pd,
            forecasted_revenue={
                "co_hosting_fee_pct": forecasted_revenue.co_hosting_fee_pct,
                "annual_re_appreciation_pct": (
                    forecasted_revenue.annual_re_appreciation_pct
                ),
                "scenarios": scenarios,
            },
            taxes=tax,
            y1_coc_incl_tax_savings=y1_coc,
            optimization_total=money(optimization_total),
            operating_expense_total=money(opex_total),
            total_oop=total_oop,
            prr=percentage(mid_revenue / pd["purchase_price"]),
            budget_to_pp=percentage(total_oop / pd["purchase_price"]),
            low_gross_revenue=scenarios["low"]["forecasted_revenue"],
            mid_gross_revenue=mid_revenue,
            high_gross_revenue=scenarios["high"]["forecasted_revenue"],
            l_cash_on_cash=scenarios["low"]["cash_on_cash_pct"],
            m_cash_on_cash=scenarios["mid"]["cash_on_cash_pct"],
            h_cash_on_cash=scenarios["high"]["cash_on_cash_pct"],
        )

    @staticmethod
    def calculate_purchase_details(purchase_details: PurchaseDetailsInput) -> dict:
        data = purchase_details.model_dump()
        price = data["purchase_price"]
        down_payment_amount = price * data["down_payment_pct"]
        return {
            **data,
            "down_payment_amount": money(down_payment_amount),
            "loan_amount": money(price - down_payment_amount),
            "closing_costs_amount": money(price * data["closing_costs_pct"]),
        }

    @staticmethod
    def monthly_payment(pd: dict) -> Decimal:
        loan = pd["loan_amount"]
        n = Decimal(pd["mortgage_years"]) * _MONTHS_IN_YEAR
        r = pd["interest_rate"] / _MONTHS_IN_YEAR
        if loan <= 0:
            return Decimal("0")
        if r == 0:
            return loan / n
        growth = (Decimal("1") + r) ** int(n)
        return loan * r * growth / (growth - Decimal("1"))

    @classmethod
    def annual_debt_service(cls, pd: dict) -> Decimal:
        return cls.monthly_payment(pd) * _MONTHS_IN_YEAR

    @classmethod
    def year_one_principal_pay_down(cls, pd: dict) -> Decimal:
        """Sum of the principal portions of the first twelve payments."""
        payment = cls.monthly_payment(pd)
        balance = pd["loan_amount"]
        r = pd["interest_rate"] / _MONTHS_IN_YEAR
        paid = Decimal("0")
        for _ in range(12):
            interest = balance * r
            principal = payment - interest
            paid += principal
            balance -= principal
        return paid

    @staticmethod
    def calculate_taxes(
        taxes: UnderwritingTaxInput,
        purchase_price: Decimal,
        optimization_total: Decimal,
    ) -> dict:
        improvement_basis = (
            purchase_price * (Decimal("1") - taxes.land_assumptions_pct)
            + optimization_total
        )
        short_life_assets = improvement_basis * taxes.sla_multiplier_pct
        y1_loss = short_life_assets * taxes.bonus_amount_pct
        tax_savings = taxes.tax_rate_pct * y1_loss
        return {
            **taxes.model_dump(),
            "improvement_basis": money(improvement_basis),
            "estimated_short_life_assets": money(short_life_assets),
            "y1_loss_from_depreciation": money(y1_loss),
            "tax_savings": money(tax_savings),
        }
