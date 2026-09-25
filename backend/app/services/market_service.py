from app.repositories.market_repository import MarketRepository
from app.schemas.market import MarketListResult, MarketRead


class MarketService:
    def __init__(self, repository: MarketRepository):
        self.repository = repository

    async def list(self, *, is_active: bool | None = None) -> MarketListResult:
        rows = await self.repository.list(is_active=is_active)
        items = [self._read(market, count) for market, count in rows]
        return MarketListResult(items=items, total=len(items))

    async def get(self, market_id: int) -> MarketRead:
        row = await self.repository.get(market_id)
        if row is None:
            raise LookupError(f"Market {market_id} not found")
        return self._read(*row)

    @staticmethod
    def _read(market, property_count: int) -> MarketRead:
        return MarketRead.model_validate(market).model_copy(
            update={"property_count": property_count}
        )
