from app.repositories.property_repository import PropertyRepository
from app.schemas.property import PropertyListResult, PropertyRead


class PropertyService:
    def __init__(self, repository: PropertyRepository):
        self.repository = repository

    async def list(self, *, search: str | None = None) -> PropertyListResult:
        rows = await self.repository.list(search=search)
        return PropertyListResult(
            items=[PropertyRead.model_validate(r) for r in rows], total=len(rows)
        )

    async def get(self, zpid: str) -> PropertyRead:
        row = await self.repository.get(zpid)
        if row is None:
            raise LookupError(f"Property {zpid} not found")
        return PropertyRead.model_validate(row)
