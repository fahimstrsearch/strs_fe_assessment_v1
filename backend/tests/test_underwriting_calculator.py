from decimal import Decimal

from app.schemas.underwriting import (
    ForecastedRevenueInput,
    OperatingExpenseInput,
    OptimizationItemInput,
    PurchaseDetailsInput,
    UnderwritingTaxInput,
)
from app.services.underwriting_calculator import UnderwritingCalculator


def _inputs():
    return dict(
        purchase_details=PurchaseDetailsInput(
            purchase_price=Decimal("500000"),
            down_payment_pct=Decimal("0.20"),
            interest_rate=Decimal("0.07"),
            mortgage_years=30,
            closing_costs_pct=Decimal("0.03"),
        ),
        forecasted_revenue=ForecastedRevenueInput(
            co_hosting_fee_pct=Decimal("0"),
            annual_re_appreciation_pct=Decimal("0.03"),
            scenarios={
                "low": {"forecasted_revenue": Decimal("100000")},
                "mid": {"forecasted_revenue": Decimal("120000")},
                "high": {"forecasted_revenue": Decimal("140000")},
            },
        ),
        taxes=UnderwritingTaxInput(
            land_assumptions_pct=Decimal("0.20"),
            sla_multiplier_pct=Decimal("0.25"),
            bonus_amount_pct=Decimal("0.60"),
            tax_rate_pct=Decimal("0.37"),
        ),
        optimization_items=[
            OptimizationItemInput(category="Furniture", total_price=Decimal("40000")),
            OptimizationItemInput(category="Hot tub", total_price=Decimal("20000")),
        ],
        operating_expenses=[
            OperatingExpenseInput(
                expense_name="Utilities", monthly_amount=Decimal("500")
            ),
            OperatingExpenseInput(
                expense_name="Insurance", monthly_amount=Decimal("300")
            ),
        ],
    )


def test_totals_and_ratios():
    result = UnderwritingCalculator().calculate(**_inputs())
    assert result.optimization_total == Decimal("60000.00")
    assert result.operating_expense_total == Decimal("800.00")
    # 100k down + 15k closing + 60k optimization
    assert result.total_oop == Decimal("175000.00")
    assert result.prr == Decimal("0.2400")
    assert result.budget_to_pp == Decimal("0.3500")
    assert result.mid_gross_revenue == Decimal("120000.00")


def test_debt_service_matches_standard_amortization():
    pd = UnderwritingCalculator.calculate_purchase_details(
        _inputs()["purchase_details"]
    )
    # $400k @ 7% / 30y => $2,661.21 per month
    monthly = UnderwritingCalculator.monthly_payment(pd)
    assert round(monthly, 2) == Decimal("2661.21")
    paydown = UnderwritingCalculator.year_one_principal_pay_down(pd)
    assert Decimal("4000") < paydown < Decimal("4200")


def test_cash_on_cash_ordering_and_tax_savings():
    result = UnderwritingCalculator().calculate(**_inputs())
    assert result.l_cash_on_cash < result.m_cash_on_cash < result.h_cash_on_cash
    mid = result.forecasted_revenue["scenarios"]["mid"]
    expected_coc = mid["annual_free_cash_flow"] / result.total_oop
    assert abs(result.m_cash_on_cash - expected_coc) < Decimal("0.0001")
    # improvement basis = 500k*0.8 + 60k = 460k; SLA 115k; y1 loss 69k; savings 25,530
    assert result.taxes["tax_savings"] == Decimal("25530.00")
    assert result.y1_coc_incl_tax_savings["mid_pct"] > result.m_cash_on_cash
