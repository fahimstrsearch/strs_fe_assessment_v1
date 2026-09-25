from fastapi import HTTPException

from app.core.logger import logger
from app.schemas.property import PropertyListResult, PropertyRead
from app.services.property_service import PropertyService


class PropertyController:
    def __init__(self, service: PropertyService):
        self.service = service

    async def list_properties(
        self, search: str | None, market_id: int | None = None
    ) -> PropertyListResult:
        try:
            return await self.service.list(search=search, market_id=market_id)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error("properties.list.error", error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch properties"
            ) from e

    async def get_property(self, zpid: str) -> PropertyRead:
        try:
            return await self.service.get(zpid)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error("properties.get.error", zpid=zpid, error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to fetch property"
            ) from e
