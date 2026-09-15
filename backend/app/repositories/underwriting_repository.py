from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Underwriting,
    UnderwritingCompSet,
    UnderwritingDetail,
    UnderwritingOperatingExpense,
    UnderwritingOptimizationItem,
    UnderwritingTax,
)

_LOAD_CHILDREN = (
    selectinload(Underwriting.detail),
    selectinload(Underwriting.taxes),
    selectinload(Underwriting.optimization_items),
    selectinload(Underwriting.operating_expenses),
    selectinload(Underwriting.comp_set),
)


class UnderwritingRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, underwriting_id: int) -> Underwriting | None:
        stmt = (
            select(Underwriting)
            .options(*_LOAD_CHILDREN)
            .where(Underwriting.id == underwriting_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def get_reference_for_zpid(self, zpid: str) -> Underwriting | None:
        stmt = (
            select(Underwriting)
            .options(*_LOAD_CHILDREN)
            .where(Underwriting.zpid == zpid, Underwriting.is_reference.is_(True))
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_trainee_underwritings(self) -> list[Underwriting]:
        """All non-reference rows, newest first, without child rows."""
        stmt = (
            select(Underwriting)
            .where(Underwriting.is_reference.is_(False))
            .order_by(Underwriting.created_at.desc(), Underwriting.id.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def create(self, underwriting: Underwriting) -> Underwriting:
        self.db.add(underwriting)
        await self.db.flush()
        return underwriting

    def ensure_detail(self, underwriting: Underwriting) -> UnderwritingDetail:
        if underwriting.detail is None:
            underwriting.detail = UnderwritingDetail()
        return underwriting.detail

    def ensure_taxes(self, underwriting: Underwriting) -> UnderwritingTax:
        if underwriting.taxes is None:
            underwriting.taxes = UnderwritingTax()
        return underwriting.taxes

    @staticmethod
    def replace_optimization_items(
        underwriting: Underwriting, rows: list[dict]
    ) -> None:
        underwriting.optimization_items = [
            UnderwritingOptimizationItem(**row, sort_order=i)
            for i, row in enumerate(rows)
        ]

    @staticmethod
    def replace_operating_expenses(
        underwriting: Underwriting, rows: list[dict]
    ) -> None:
        underwriting.operating_expenses = [
            UnderwritingOperatingExpense(**row, sort_order=i)
            for i, row in enumerate(rows)
        ]

    @staticmethod
    def replace_comp_set(underwriting: Underwriting, rows: list[dict]) -> None:
        underwriting.comp_set = [
            UnderwritingCompSet(**row, sort_order=i) for i, row in enumerate(rows)
        ]

    async def commit_and_refresh(self, underwriting: Underwriting) -> Underwriting:
        underwriting_id = underwriting.id
        await self.db.commit()
        # Reload with children and the column_property totals recomputed.
        self.db.expire(underwriting)
        return await self.get_by_id(underwriting_id)
