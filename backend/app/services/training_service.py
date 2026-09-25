"""Dashboard aggregation and submission grading."""

from decimal import Decimal

from app.core.logger import logger
from app.models import TrainingSubmission
from app.repositories.property_repository import PropertyRepository
from app.repositories.training_repository import TrainingRepository
from app.repositories.underwriting_repository import UnderwritingRepository
from app.schemas.training import (
    DashboardProperty,
    DashboardResult,
    DashboardSummary,
    SubmissionRead,
    SubmitUnderwritingResult,
)
from app.schemas.underwriting import SaveUnderwritingPayload, UnderwritingRead
from app.services.scoring_service import ScoringService
from app.services.underwriting_service import STARTED_STATUS, UnderwritingService


class TrainingService:
    def __init__(
        self,
        training_repository: TrainingRepository,
        underwriting_repository: UnderwritingRepository,
        property_repository: PropertyRepository,
        underwriting_service: UnderwritingService,
        scoring_service: ScoringService | None = None,
    ):
        self.training_repository = training_repository
        self.underwriting_repository = underwriting_repository
        self.property_repository = property_repository
        self.underwriting_service = underwriting_service
        self.scoring_service = scoring_service or ScoringService()

    async def dashboard(self) -> DashboardResult:
        properties = await self.property_repository.list()
        submissions = await self.training_repository.list()
        drafts = await self.underwriting_repository.list_trainee_underwritings()

        latest: dict[str, TrainingSubmission] = {}
        best: dict[str, TrainingSubmission] = {}
        attempts: dict[str, int] = {}
        for s in submissions:  # newest first
            attempts[s.zpid] = attempts.get(s.zpid, 0) + 1
            latest.setdefault(s.zpid, s)
            if s.zpid not in best or s.accuracy > best[s.zpid].accuracy:
                best[s.zpid] = s

        active_draft: dict[str, int] = {}
        for uw in drafts:  # newest first
            if uw.zpid and uw.deal_status == STARTED_STATUS:
                active_draft.setdefault(uw.zpid, uw.id)

        rows: list[DashboardProperty] = []
        for p in properties:
            if p.zpid in active_draft:
                status = "in_progress"
            elif p.zpid in latest:
                status = "submitted"
            else:
                status = "not_started"
            rows.append(
                DashboardProperty(
                    zpid=p.zpid,
                    address=p.address,
                    city=p.address_city,
                    state=p.address_state,
                    zipcode=p.address_zipcode,
                    price=p.price,
                    unformatted_price=p.unformatted_price,
                    beds=p.beds,
                    baths=p.baths,
                    area=p.area,
                    img_src=p.img_src,
                    detail_url=p.detail_url,
                    home_type=p.home_type,
                    market_id=p.market_id,
                    market_name=p.market.name if p.market else None,
                    status=status,
                    attempts=attempts.get(p.zpid, 0),
                    latest_accuracy=latest[p.zpid].accuracy
                    if p.zpid in latest
                    else None,
                    latest_rating=latest[p.zpid].rating if p.zpid in latest else None,
                    best_accuracy=best[p.zpid].accuracy if p.zpid in best else None,
                    best_rating=best[p.zpid].rating if p.zpid in best else None,
                    active_underwriting_id=active_draft.get(p.zpid),
                    latest_submission_id=latest[p.zpid].id
                    if p.zpid in latest
                    else None,
                )
            )

        scored = [r.latest_accuracy for r in rows if r.latest_accuracy is not None]
        summary = DashboardSummary(
            total_properties=len(rows),
            submitted=sum(1 for r in rows if r.status == "submitted"),
            in_progress=sum(1 for r in rows if r.status == "in_progress"),
            not_started=sum(1 for r in rows if r.status == "not_started"),
            average_accuracy=(
                (sum(scored, Decimal("0")) / len(scored)).quantize(Decimal("0.01"))
                if scored
                else None
            ),
        )
        return DashboardResult(summary=summary, properties=rows)

    async def submit(
        self, underwriting_id: int, payload: SaveUnderwritingPayload | None
    ) -> SubmitUnderwritingResult:
        underwriting = await self.underwriting_service.submit(underwriting_id, payload)
        if underwriting.zpid is None:
            raise LookupError("Underwriting is not linked to a property")

        reference = await self.underwriting_repository.get_reference_for_zpid(
            underwriting.zpid
        )
        if reference is None:
            raise LookupError(
                f"No reference underwriting exists for property {underwriting.zpid}"
            )

        result = self.scoring_service.score(underwriting, reference)
        submission = TrainingSubmission(
            underwriting_id=underwriting.id,
            reference_underwriting_id=reference.id,
            zpid=underwriting.zpid,
            rating=result.rating,
            accuracy=result.accuracy,
            breakdown=result.model_dump(mode="json"),
        )
        await self.training_repository.create(submission)
        underwriting.deal_score = max(1, min(100, int(round(result.accuracy))))
        await self.training_repository.db.commit()
        await self.training_repository.db.refresh(submission)

        logger.info(
            "training.submitted",
            underwriting_id=underwriting.id,
            zpid=underwriting.zpid,
            rating=result.rating,
            accuracy=str(result.accuracy),
        )
        return SubmitUnderwritingResult(
            submission=SubmissionRead.model_validate(submission),
            underwriting=UnderwritingRead.model_validate(
                await self.underwriting_repository.get_by_id(underwriting.id)
            ),
            dashboard=await self.dashboard(),
        )

    async def list_submissions(
        self, *, zpid: str | None = None
    ) -> list[SubmissionRead]:
        rows = await self.training_repository.list(zpid=zpid)
        return [SubmissionRead.model_validate(r) for r in rows]

    async def get_submission(self, submission_id: int) -> SubmissionRead:
        row = await self.training_repository.get(submission_id)
        if row is None:
            raise LookupError(f"Submission {submission_id} not found")
        return SubmissionRead.model_validate(row)
