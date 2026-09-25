from app.repositories.market_repository import MarketRepository
from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyListResult, PropertyRead


class PropertyService:
    def __init__(
        self,
        repository: PropertyRepository,
        market_repository: MarketRepository | None = None,
    ):
        self.repository = repository
        self.market_repository = market_repository

    async def list(
        self, *, search: str | None = None, market_id: int | None = None
    ) -> PropertyListResult:
        if market_id is not None and self.market_repository is not None:
            if not await self.market_repository.exists(market_id):
                raise LookupError(f"Market {market_id} not found")
        rows = await self.repository.list(search=search, market_id=market_id)
        return PropertyListResult(
            items=[PropertyRead.model_validate(r) for r in rows], total=len(rows)
        )

    async def get(self, zpid: str) -> PropertyRead:
        row = await self.repository.get(zpid)
        if row is None:
            raise LookupError(f"Property {zpid} not found")
        return PropertyRead.model_validate(row)
