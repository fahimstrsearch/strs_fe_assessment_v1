from fastapi import HTTPException

from app.core.logger import logger
from app.schemas.underwriting import (
    SaveUnderwritingPayload,
    StartUnderwritingPayload,
    UnderwritingRead,
)
from app.services.underwriting_service import UnderwritingService


class UnderwritingController:
    def __init__(self, service: UnderwritingService):
        self.service = service

    async def start(self, payload: StartUnderwritingPayload) -> UnderwritingRead:
        try:
            return await self.service.start(payload.zpid)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error("underwritings.start.error", zpid=payload.zpid, error=str(e))
            raise HTTPException(
                status_code=500, detail="Failed to start underwriting"
            ) from e

    async def get(self, underwriting_id: int) -> UnderwritingRead:
        try:
            return await self.service.get(underwriting_id)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except Exception as e:
            logger.error(
                "underwritings.get.error", underwriting_id=underwriting_id, error=str(e)
            )
            raise HTTPException(
                status_code=500, detail="Failed to fetch underwriting"
            ) from e

    async def save(
        self, underwriting_id: int, payload: SaveUnderwritingPayload
    ) -> UnderwritingRead:
        try:
            return await self.service.save(underwriting_id, payload)
        except LookupError as e:
            raise HTTPException(status_code=404, detail=str(e)) from e
        except PermissionError as e:
            raise HTTPException(status_code=403, detail=str(e)) from e
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e)) from e
        except Exception as e:
            logger.error(
                "underwritings.save.error",
                underwriting_id=underwriting_id,
                error=str(e),
            )
            raise HTTPException(
                status_code=500, detail="Failed to save underwriting"
            ) from e
