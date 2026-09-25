from fastapi import HTTPException

from app.core.logger import logger
from app.schemas.market import MarketListResult, MarketRead
from app.services.market_service import MarketService


class MarketController:
    def __init__(self, service: MarketService):
        self.service = service

    async def list_markets(self, is_active: bool | None) -> MarketListResult:
        try:
            return await self.service.list(is_active=is_active)
        except Exception as e:
            logger.error("markets.list.error", error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch markets"
            ) from e

    async def get_market(self, market_id: int) -> MarketRead:
        try:
            return await self.service.get(market_id)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error("markets.get.error", market_id=market_id, error=str(e))
            raise HTTPException(status_code=500, detail="Failed to fetch market") from e
