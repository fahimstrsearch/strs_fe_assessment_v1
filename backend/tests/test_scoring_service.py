from decimal import Decimal

from app.services.scoring_service import (
    BEST_THRESHOLD,
    MEDIUM_THRESHOLD,
    ScoringService,
    deviation_from,
    grade,
)

REFERENCE = {"mid_gross_revenue": Decimal("120000")}


def _rate(candidate: str | None) -> tuple[str, Decimal]:
    value = None if candidate is None else Decimal(candidate)
    result = ScoringService().score({"mid_gross_revenue": value}, REFERENCE)
    return result.rating, result.accuracy


def test_exact_match_is_best():
    assert _rate("120000") == ("best", Decimal("100.00"))


def test_within_ten_percent_is_best():
    # 108k and 132k are exactly 10% either side of 120k.
    assert _rate("108000") == ("best", Decimal("100.00"))
    assert _rate("132000") == ("best", Decimal("100.00"))
    assert _rate("115000") == ("best", Decimal("100.00"))


def test_between_ten_and_twenty_five_percent_is_medium():
    # 10.01% off tips it out of best; 25% is still medium.
    assert _rate("107900") == ("medium", Decimal("70.00"))
    assert _rate("90000") == ("medium", Decimal("70.00"))
    assert _rate("150000") == ("medium", Decimal("70.00"))


def test_beyond_twenty_five_percent_is_low():
    assert _rate("89000") == ("low", Decimal("40.00"))
    assert _rate("200000") == ("low", Decimal("40.00"))
    assert _rate("0") == ("low", Decimal("40.00"))


def test_missing_forecast_is_low():
    assert _rate(None) == ("low", Decimal("40.00"))


def test_zero_reference_does_not_divide_by_zero():
    assert deviation_from(Decimal("0"), Decimal("0")) == Decimal("0")
    assert deviation_from(Decimal("5"), Decimal("0")) == Decimal("1")


def test_grade_boundaries_are_inclusive():
    assert grade(BEST_THRESHOLD)[0] == "best"
    assert grade(MEDIUM_THRESHOLD)[0] == "medium"


def test_result_explains_the_decision():
    result = ScoringService().score({"mid_gross_revenue": Decimal("150000")}, REFERENCE)
    assert result.metric == "mid_gross_revenue"
    assert result.candidate == Decimal("150000")
    assert result.reference == Decimal("120000")
    assert result.deviation == Decimal("0.2500")
    assert result.best_threshold == Decimal("0.10")
    assert result.medium_threshold == Decimal("0.25")
