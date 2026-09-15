from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TrainingSubmission


class TrainingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, submission: TrainingSubmission) -> TrainingSubmission:
        self.db.add(submission)
        await self.db.flush()
        return submission

    async def list(self, *, zpid: str | None = None) -> list[TrainingSubmission]:
        stmt = select(TrainingSubmission).order_by(
            TrainingSubmission.submitted_at.desc(), TrainingSubmission.id.desc()
        )
        if zpid:
            stmt = stmt.where(TrainingSubmission.zpid == zpid)
        return list((await self.db.execute(stmt)).scalars().all())

    async def get(self, submission_id: int) -> TrainingSubmission | None:
        return await self.db.get(TrainingSubmission, submission_id)
