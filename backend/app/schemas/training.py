from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.underwriting import UnderwritingRead


class ScoreResult(BaseModel):
    """Outcome of grading one attempt against the reference."""

    # best | medium | low
    rating: str
    # 100 / 70 / 40, matching the rating.
    accuracy: Decimal
    metric: str
    label: str
    candidate: Decimal | None
    reference: Decimal | None
    # |candidate - reference| / reference
    deviation: Decimal
    best_threshold: Decimal
    medium_threshold: Decimal


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    underwriting_id: int
    reference_underwriting_id: int | None
    zpid: str
    # best | medium | low
    rating: str
    accuracy: Decimal
    breakdown: ScoreResult
    submitted_at: datetime


class DashboardProperty(BaseModel):
    zpid: str
    address: str | None
    city: str | None
    state: str | None
    zipcode: str | None
    price: str | None
    unformatted_price: str | None
    beds: int | None
    baths: float | None
    area: int | None
    img_src: str | None
    detail_url: str | None
    home_type: str | None
    market_id: int | None
    market_name: str | None
    # not_started | in_progress | submitted
    status: str
    attempts: int
    latest_accuracy: Decimal | None
    latest_rating: str | None
    best_accuracy: Decimal | None
    best_rating: str | None
    # Draft to resume, if one exists.
    active_underwriting_id: int | None
    latest_submission_id: int | None


class DashboardSummary(BaseModel):
    total_properties: int
    submitted: int
    in_progress: int
    not_started: int
    average_accuracy: Decimal | None


class DashboardResult(BaseModel):
    summary: DashboardSummary
    properties: list[DashboardProperty]


class SubmitUnderwritingResult(BaseModel):
    submission: SubmissionRead
    underwriting: UnderwritingRead
    dashboard: DashboardResult
