from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Property


class PropertyRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(
        self, *, search: str | None = None, market_id: int | None = None
    ) -> list[Property]:
        stmt = select(Property).where(Property.remove_listing.is_not(True))
        if market_id is not None:
            stmt = stmt.where(Property.market_id == market_id)
        if search:
            like = f"%{search}%"
            stmt = stmt.where(
                Property.address.ilike(like)
                | Property.address_city.ilike(like)
                | Property.address_state.ilike(like)
            )
        result = await self.db.execute(
            stmt.order_by(Property.created_at, Property.zpid)
        )
        return list(result.scalars().all())

    async def count(self) -> int:
        return (
            await self.db.scalar(
                select(func.count())
                .select_from(Property)
                .where(Property.remove_listing.is_not(True))
            )
            or 0
        )

    async def get(self, zpid: str) -> Property | None:
        return await self.db.get(Property, zpid)
