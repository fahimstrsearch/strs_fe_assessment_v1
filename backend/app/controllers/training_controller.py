from fastapi import HTTPException

from app.core.logger import logger
from app.schemas.training import (
    DashboardResult,
    SubmissionRead,
    SubmitUnderwritingResult,
)
from app.schemas.underwriting import SaveUnderwritingPayload
from app.services.training_service import TrainingService


class TrainingController:
    def __init__(self, service: TrainingService):
        self.service = service

    async def dashboard(self) -> DashboardResult:
        try:
            return await self.service.dashboard()
        except Exception as e:
            logger.error("training.dashboard.error", error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to build dashboard"
            ) from e

    async def submit(
        self, underwriting_id: int, payload: SaveUnderwritingPayload | None
    ) -> SubmitUnderwritingResult:
        try:
            return await self.service.submit(underwriting_id, payload)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except Exception as e:
            logger.error(
                "training.submit.error", underwriting_id=underwriting_id, error=str(e)
            )
            raise HTTPException(
                status_code=500, detail="Failed to submit underwriting"
            ) from e

    async def list_submissions(self, zpid: str | None) -> list[SubmissionRead]:
        try:
            return await self.service.list_submissions(zpid=zpid)
        except Exception as e:
            logger.error("training.submissions.error", zpid=zpid, error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch submissions"
            ) from e

    async def get_submission(self, submission_id: int) -> SubmissionRead:
        try:
            return await self.service.get_submission(submission_id)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error(
                "training.submission.error", submission_id=submission_id, error=str(e)
            )
            raise HTTPException(
                status_code=500, detail="Failed to fetch submission"
            ) from e
