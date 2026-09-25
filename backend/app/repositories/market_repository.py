from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Market, Property


class MarketRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _with_counts(self) -> Select:
        property_count = (
            select(func.count())
            .select_from(Property)
            .where(
                Property.market_id == Market.id,
                Property.remove_listing.is_not(True),
            )
            .scalar_subquery()
        )
        return select(Market, property_count.label("property_count"))

    async def list(self, *, is_active: bool | None = None) -> list[tuple[Market, int]]:
        stmt = self._with_counts()
        if is_active is not None:
            stmt = stmt.where(Market.is_active.is_(is_active))
        result = await self.db.execute(stmt.order_by(Market.name))
        return [(row.Market, row.property_count) for row in result]

    async def get(self, market_id: int) -> tuple[Market, int] | None:
        stmt = self._with_counts().where(Market.id == market_id)
        row = (await self.db.execute(stmt)).one_or_none()
        return (row.Market, row.property_count) if row else None

    async def exists(self, market_id: int) -> bool:
        return (
            await self.db.scalar(select(Market.id).where(Market.id == market_id))
        ) is not None
