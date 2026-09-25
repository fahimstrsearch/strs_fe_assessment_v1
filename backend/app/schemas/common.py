from pydantic import BaseModel


class ErrorResponse(BaseModel):
    """Shape of every error FastAPI raises through ``HTTPException``."""

    detail: str
