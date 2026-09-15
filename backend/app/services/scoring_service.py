"""Grades a trainee underwriting against the analyst reference.

Each metric carries a weight (points out of 100) and a tolerance. A candidate
value within tolerance of the reference earns the full weight; the score then
decays linearly to zero at three times the tolerance. Money metrics use
relative deviation; percentage metrics (cash-on-cash) use absolute deviation
in percentage points so a 0% vs 2% guess is not "infinitely" wrong.
"""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.schemas.training import MetricScore, ScoreResult

_TWO_PLACES = Decimal("0.01")
_FOUR_PLACES = Decimal("0.0001")


@dataclass(frozen=True)
class MetricRule:
    metric: str
    label: str
    weight: Decimal
    tolerance: Decimal
    relative: bool = True


SCORING_RULES: tuple[MetricRule, ...] = (
    MetricRule("purchase_price", "Purchase price", Decimal("15"), Decimal("0.05")),
    MetricRule(
        "mid_gross_revenue", "Mid revenue forecast", Decimal("25"), Decimal("0.15")
    ),
    MetricRule(
        "operating_expense_total",
        "Monthly operating expenses",
        Decimal("15"),
        Decimal("0.20"),
    ),
    MetricRule(
        "optimization_total", "Optimization budget", Decimal("10"), Decimal("0.25")
    ),
    MetricRule("total_oop", "Total out of pocket", Decimal("15"), Decimal("0.15")),
    MetricRule(
        "m_cash_on_cash",
        "Mid cash-on-cash",
        Decimal("20"),
        Decimal("0.03"),
        relative=False,
    ),
)


def _get(obj: Any, name: str) -> Decimal | None:
    value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    return None if value is None else Decimal(str(value))


def score_metric(
    rule: MetricRule, candidate: Decimal | None, reference: Decimal | None
) -> MetricScore:
    deviation: Decimal | None
    if candidate is None or reference is None:
        deviation, fraction = None, Decimal("0")
    elif rule.relative:
        if reference == 0:
            deviation = Decimal("0") if candidate == 0 else Decimal("1")
        else:
            deviation = abs(candidate - reference) / abs(reference)
        fraction = _decay(deviation, rule.tolerance)
    else:
        deviation = abs(candidate - reference)
        fraction = _decay(deviation, rule.tolerance)

    points = (rule.weight * fraction).quantize(_TWO_PLACES, rounding=ROUND_HALF_UP)
    return MetricScore(
        metric=rule.metric,
        label=rule.label,
        weight=rule.weight,
        candidate=candidate,
        reference=reference,
        deviation=None if deviation is None else deviation.quantize(_FOUR_PLACES),
        tolerance=rule.tolerance,
        score=fraction.quantize(_FOUR_PLACES),
        points=points,
    )


def _decay(deviation: Decimal, tolerance: Decimal) -> Decimal:
    if deviation <= tolerance:
        return Decimal("1")
    remaining = Decimal("1") - (deviation - tolerance) / (tolerance * 2)
    return max(Decimal("0"), remaining)


class ScoringService:
    def __init__(self, rules: tuple[MetricRule, ...] = SCORING_RULES):
        self.rules = rules

    def score(self, candidate: Any, reference: Any) -> ScoreResult:
        breakdown = [
            score_metric(
                rule, _get(candidate, rule.metric), _get(reference, rule.metric)
            )
            for rule in self.rules
        ]
        total_weight = sum((r.weight for r in self.rules), Decimal("0"))
        earned = sum((m.points for m in breakdown), Decimal("0"))
        accuracy = (earned / total_weight * Decimal("100")).quantize(
            _TWO_PLACES, rounding=ROUND_HALF_UP
        )
        return ScoreResult(accuracy=accuracy, breakdown=breakdown)
