"""HTTP routes. Wires request -> controller -> service -> repository per call."""

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.controllers.market_controller import MarketController
from app.controllers.property_controller import PropertyController
from app.controllers.training_controller import TrainingController
from app.controllers.underwriting_controller import UnderwritingController
from app.core.database import get_db
from app.repositories.market_repository import MarketRepository
from app.repositories.property_repository import PropertyRepository
from app.repositories.training_repository import TrainingRepository
from app.repositories.underwriting_repository import UnderwritingRepository
from app.schemas.common import ErrorResponse
from app.schemas.market import MarketListResult, MarketRead
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
from app.services.market_service import MarketService
from app.services.property_service import PropertyService
from app.services.training_service import TrainingService
from app.services.underwriting_service import UnderwritingService

router = APIRouter(prefix="/api")

DB = Annotated[AsyncSession, Depends(get_db)]


def _errors(descriptions: dict[int, str]) -> dict:
    """Document the errors a route raises so generated clients can see them."""
    return {
        code: {"model": ErrorResponse, "description": text}
        for code, text in descriptions.items()
    }


def _market_controller(db: DB) -> MarketController:
    return MarketController(MarketService(MarketRepository(db)))


def _property_controller(db: DB) -> PropertyController:
    return PropertyController(
        PropertyService(PropertyRepository(db), MarketRepository(db))
    )


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


MarketCtl = Annotated[MarketController, Depends(_market_controller)]
PropertyCtl = Annotated[PropertyController, Depends(_property_controller)]
UnderwritingCtl = Annotated[UnderwritingController, Depends(_underwriting_controller)]
TrainingCtl = Annotated[TrainingController, Depends(_training_controller)]


@router.get("/health", tags=["meta"])
async def health() -> dict:
    """Liveness probe."""
    return {"status": "ok"}


# ---------------------------------------------------------------- dashboard --


@router.get(
    "/dashboard",
    response_model=DashboardResult,
    tags=["training"],
    responses=_errors({500: "Failed to build dashboard"}),
)
async def get_dashboard(controller: TrainingCtl):
    """Property list with per-property training status and accuracy."""
    return await controller.dashboard()


# ------------------------------------------------------------------ markets --


@router.get(
    "/markets",
    response_model=MarketListResult,
    tags=["markets"],
    responses=_errors({500: "Failed to fetch markets"}),
)
async def list_markets(
    controller: MarketCtl,
    is_active: bool | None = Query(
        None, description="Filter to active (true) or retired (false) markets."
    ),
):
    """Every market, with a live count of the properties attached to it."""
    return await controller.list_markets(is_active)


@router.get(
    "/markets/{market_id}",
    response_model=MarketRead,
    tags=["markets"],
    responses=_errors({404: "No market with this id", 500: "Failed to fetch market"}),
)
async def get_market(market_id: int, controller: MarketCtl):
    """One market, with its property count."""
    return await controller.get_market(market_id)


# --------------------------------------------------------------- properties --


@router.get(
    "/properties",
    response_model=PropertyListResult,
    tags=["properties"],
    responses=_errors(
        {
            404: "The requested market_id does not exist",
            500: "Failed to fetch properties",
        }
    ),
)
async def list_properties(
    controller: PropertyCtl,
    search: str | None = Query(None),
    market_id: int | None = Query(None, description="Only properties in this market."),
):
    """Property list, optionally narrowed by free-text search and/or market."""
    return await controller.list_properties(search, market_id)


@router.get(
    "/properties/{zpid}",
    response_model=PropertyRead,
    tags=["properties"],
    responses=_errors(
        {404: "No property with this zpid", 500: "Failed to fetch property"}
    ),
)
async def get_property(zpid: str, controller: PropertyCtl):
    """One property, including its market."""
    return await controller.get_property(zpid)


# ------------------------------------------------------------ underwritings --


@router.post(
    "/underwritings",
    response_model=UnderwritingRead,
    status_code=201,
    tags=["underwritings"],
    responses=_errors(
        {404: "No property with this zpid", 500: "Failed to start underwriting"}
    ),
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
    responses=_errors(
        {404: "No underwriting with this id", 500: "Failed to fetch underwriting"}
    ),
)
async def get_underwriting(underwriting_id: int, controller: UnderwritingCtl):
    """Draft, with detail, taxes, line items and derived numbers."""
    return await controller.get(underwriting_id)


@router.put(
    "/underwritings/{underwriting_id}",
    response_model=UnderwritingRead,
    tags=["underwritings"],
    responses=_errors(
        {
            403: "Reference underwritings are read-only",
            404: "No underwriting with this id",
            500: "Failed to save underwriting",
        }
    ),
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
    responses=_errors(
        {
            403: "Reference underwritings are read-only",
            404: "No underwriting, linked property, or reference to grade against",
            500: "Failed to submit underwriting",
        }
    ),
)
async def submit_underwriting(
    underwriting_id: int,
    controller: TrainingCtl,
    payload: SaveUnderwritingPayload | None = Body(default=None),
):
    """Finalise, grade against the reference, and return the refreshed dashboard."""
    return await controller.submit(underwriting_id, payload)


# -------------------------------------------------------------- submissions --


@router.get(
    "/submissions",
    response_model=list[SubmissionRead],
    tags=["training"],
    responses=_errors({500: "Failed to fetch submissions"}),
)
async def list_submissions(controller: TrainingCtl, zpid: str | None = Query(None)):
    """Attempt history, newest first, optionally for one property."""
    return await controller.list_submissions(zpid)


@router.get(
    "/submissions/{submission_id}",
    response_model=SubmissionRead,
    tags=["training"],
    responses=_errors(
        {404: "No submission with this id", 500: "Failed to fetch submission"}
    ),
)
async def get_submission(submission_id: int, controller: TrainingCtl):
    """One graded attempt, with its full score breakdown."""
    return await controller.get_submission(submission_id)
