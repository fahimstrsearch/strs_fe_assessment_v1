"""Grades a trainee underwriting against the analyst reference.

One number decides the grade: the mid-scenario forecasted revenue. We measure
how far the trainee's forecast sits from the analyst's, then drop it into one
of three bands with a plain if/else.

    deviation = |candidate - reference| / reference

    deviation <= 10%   -> best    -> 100
    deviation <= 25%   -> medium  ->  70
    anything else      -> low     ->  40
"""

from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from app.schemas.training import ScoreResult

#: The single metric the grade is based on.
SCORED_METRIC = "mid_gross_revenue"
SCORED_LABEL = "Mid revenue forecast"

#: Deviation bands, as a fraction of the reference forecast.
BEST_THRESHOLD = Decimal("0.10")
MEDIUM_THRESHOLD = Decimal("0.25")

#: Score awarded for each band, out of 100.
BEST_SCORE = Decimal("100")
MEDIUM_SCORE = Decimal("70")
LOW_SCORE = Decimal("40")

BEST = "best"
MEDIUM = "medium"
LOW = "low"

_TWO_PLACES = Decimal("0.01")
_FOUR_PLACES = Decimal("0.0001")


def _get(obj: Any, name: str) -> Decimal | None:
    value = obj.get(name) if isinstance(obj, dict) else getattr(obj, name, None)
    return None if value is None else Decimal(str(value))


def deviation_from(candidate: Decimal | None, reference: Decimal | None) -> Decimal:
    """How far off the candidate is, as a fraction of the reference.

    A missing value on either side, or a guess against a zero reference, counts
    as fully wrong (1.0) rather than blowing up.
    """
    if candidate is None or reference is None:
        return Decimal("1")
    if reference == 0:
        return Decimal("0") if candidate == 0 else Decimal("1")
    return abs(candidate - reference) / abs(reference)


def grade(deviation: Decimal) -> tuple[str, Decimal]:
    """Map a deviation onto its band and score."""
    if deviation <= BEST_THRESHOLD:
        return BEST, BEST_SCORE
    elif deviation <= MEDIUM_THRESHOLD:
        return MEDIUM, MEDIUM_SCORE
    else:
        return LOW, LOW_SCORE


class ScoringService:
    def score(self, candidate: Any, reference: Any) -> ScoreResult:
        candidate_revenue = _get(candidate, SCORED_METRIC)
        reference_revenue = _get(reference, SCORED_METRIC)

        deviation = deviation_from(candidate_revenue, reference_revenue)
        rating, accuracy = grade(deviation)

        return ScoreResult(
            rating=rating,
            accuracy=accuracy.quantize(_TWO_PLACES, rounding=ROUND_HALF_UP),
            metric=SCORED_METRIC,
            label=SCORED_LABEL,
            candidate=candidate_revenue,
            reference=reference_revenue,
            deviation=deviation.quantize(_FOUR_PLACES),
            best_threshold=BEST_THRESHOLD,
            medium_threshold=MEDIUM_THRESHOLD,
        )
