from decimal import Decimal

from app.services.scoring_service import MetricRule, ScoringService, score_metric

REFERENCE = {
    "purchase_price": Decimal("500000"),
    "mid_gross_revenue": Decimal("120000"),
    "operating_expense_total": Decimal("2500"),
    "optimization_total": Decimal("60000"),
    "total_oop": Decimal("175000"),
    "m_cash_on_cash": Decimal("0.1500"),
}


def test_identical_submission_scores_100():
    result = ScoringService().score(REFERENCE, REFERENCE)
    assert result.accuracy == Decimal("100.00")
    assert all(m.score == Decimal("1") for m in result.breakdown)


def test_missing_metric_earns_zero_for_that_metric():
    candidate = {**REFERENCE, "m_cash_on_cash": None}
    result = ScoringService().score(candidate, REFERENCE)
    coc = next(m for m in result.breakdown if m.metric == "m_cash_on_cash")
    assert coc.points == Decimal("0")
    assert result.accuracy == Decimal("80.00")


def test_within_tolerance_is_full_credit():
    rule = MetricRule("x", "x", Decimal("10"), Decimal("0.10"))
    assert score_metric(rule, Decimal("109"), Decimal("100")).points == Decimal("10")


def test_linear_decay_to_zero_at_three_times_tolerance():
    rule = MetricRule("x", "x", Decimal("10"), Decimal("0.10"))
    # 20% off: halfway through the decay band -> half credit.
    assert score_metric(rule, Decimal("120"), Decimal("100")).points == Decimal("5.00")
    # 30% off or worse -> zero.
    assert score_metric(rule, Decimal("130"), Decimal("100")).points == Decimal("0")
    assert score_metric(rule, Decimal("400"), Decimal("100")).points == Decimal("0")


def test_absolute_tolerance_for_percentages():
    rule = MetricRule("coc", "coc", Decimal("20"), Decimal("0.03"), relative=False)
    assert score_metric(rule, Decimal("0.12"), Decimal("0.15")).points == Decimal("20")
    assert score_metric(rule, Decimal("0.09"), Decimal("0.15")).points == Decimal(
        "10.00"
    )


def test_zero_reference_does_not_divide_by_zero():
    rule = MetricRule("x", "x", Decimal("10"), Decimal("0.10"))
    assert score_metric(rule, Decimal("0"), Decimal("0")).points == Decimal("10")
    assert score_metric(rule, Decimal("5"), Decimal("0")).points == Decimal("0")
