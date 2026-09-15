from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.schemas.underwriting import UnderwritingRead


class MetricScore(BaseModel):
    metric: str
    label: str
    weight: Decimal
    candidate: Decimal | None
    reference: Decimal | None
    # Relative deviation from the reference (absolute for percentage metrics).
    deviation: Decimal | None
    tolerance: Decimal
    # Fraction of the weight earned, 0..1.
    score: Decimal
    points: Decimal


class ScoreResult(BaseModel):
    accuracy: Decimal
    breakdown: list[MetricScore]


class SubmissionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    underwriting_id: int
    reference_underwriting_id: int | None
    zpid: str
    accuracy: Decimal
    breakdown: list[MetricScore]
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
    # not_started | in_progress | submitted
    status: str
    attempts: int
    latest_accuracy: Decimal | None
    best_accuracy: Decimal | None
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
