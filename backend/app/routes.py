"""HTTP routes. Wires request -> controller -> service -> repository per call."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.property_controller import PropertyController
from app.controllers.training_controller import TrainingController
from app.controllers.underwriting_controller import UnderwritingController
from app.core.database import get_db
from app.repositories.property_repository import PropertyRepository
from app.repositories.training_repository import TrainingRepository
from app.repositories.underwriting_repository import UnderwritingRepository
from app.schemas.property import PropertyListResult, PropertyRead
from app.schemas.training import (
    DashboardResult,
    SubmissionRead,
    SubmitUnderwritingResult,
)
from app.schemas.underwriting import (
    SaveUnderwritingPayload,
    StartUnderwritingPayload,
    UnderwritingRead,
)
from app.services.property_service import PropertyService
from app.services.training_service import TrainingService
from app.services.underwriting_service import UnderwritingService

router = APIRouter(prefix="/api")

DB = Annotated[AsyncSession, Depends(get_db)]


def _property_controller(db: DB) -> PropertyController:
    return PropertyController(PropertyService(PropertyRepository(db)))


def _underwriting_service(db: AsyncSession) -> UnderwritingService:
    return UnderwritingService(UnderwritingRepository(db), PropertyRepository(db))


def _underwriting_controller(db: DB) -> UnderwritingController:
    return UnderwritingController(_underwriting_service(db))


def _training_controller(db: DB) -> TrainingController:
    return TrainingController(
        TrainingService(
            TrainingRepository(db),
            UnderwritingRepository(db),
            PropertyRepository(db),
            _underwriting_service(db),
        )
    )


PropertyCtl = Annotated[PropertyController, Depends(_property_controller)]
UnderwritingCtl = Annotated[UnderwritingController, Depends(_underwriting_controller)]
TrainingCtl = Annotated[TrainingController, Depends(_training_controller)]


@router.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}


# ---------------------------------------------------------------- dashboard --


@router.get("/dashboard", response_model=DashboardResult, tags=["training"])
async def get_dashboard(controller: TrainingCtl):
    """Property list with per-property training status and accuracy."""
    return await controller.dashboard()


# --------------------------------------------------------------- properties --


@router.get("/properties", response_model=PropertyListResult, tags=["properties"])
async def list_properties(controller: PropertyCtl, search: str | None = Query(None)):
    return await controller.list_properties(search)


@router.get("/properties/{zpid}", response_model=PropertyRead, tags=["properties"])
async def get_property(zpid: str, controller: PropertyCtl):
    return await controller.get_property(zpid)


# ------------------------------------------------------------ underwritings --


@router.post(
    "/underwritings",
    response_model=UnderwritingRead,
    status_code=201,
    tags=["underwritings"],
)
async def start_underwriting(
    payload: StartUnderwritingPayload, controller: UnderwritingCtl
):
    """Create a draft underwriting prefilled from the chosen property."""
    return await controller.start(payload)


@router.get(
    "/underwritings/{underwriting_id}",
    response_model=UnderwritingRead,
    tags=["underwritings"],
)
async def get_underwriting(underwriting_id: int, controller: UnderwritingCtl):
    return await controller.get(underwriting_id)


@router.put(
    "/underwritings/{underwriting_id}",
    response_model=UnderwritingRead,
    tags=["underwritings"],
)
async def save_underwriting(
    underwriting_id: int, payload: SaveUnderwritingPayload, controller: UnderwritingCtl
):
    """Save a draft. Partial payloads are fine; derived numbers update when possible."""
    return await controller.save(underwriting_id, payload)


@router.post(
    "/underwritings/{underwriting_id}/submit",
    response_model=SubmitUnderwritingResult,
    tags=["training"],
)
async def submit_underwriting(
    underwriting_id: int,
    controller: TrainingCtl,
    payload: SaveUnderwritingPayload | None = Body(default=None),
):
    """Finalise, grade against the reference, and return the refreshed dashboard."""
    return await controller.submit(underwriting_id, payload)


# -------------------------------------------------------------- submissions --


@router.get("/submissions", response_model=list[SubmissionRead], tags=["training"])
async def list_submissions(controller: TrainingCtl, zpid: str | None = Query(None)):
    return await controller.list_submissions(zpid)


@router.get(
    "/submissions/{submission_id}", response_model=SubmissionRead, tags=["training"]
)
async def get_submission(submission_id: int, controller: TrainingCtl):
    return await controller.get_submission(submission_id)
