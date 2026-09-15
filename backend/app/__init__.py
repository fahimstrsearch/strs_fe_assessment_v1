from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.core.logger  # noqa: F401 — configures logging at import
from app.core.config import get_config
from app.core.database import engine
from app.core.logger import logger
from app.routes import router


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    yield
    await engine.dispose()
    logger.info("db.engine_disposed")


def create_app() -> FastAPI:
    config = get_config()

    application = FastAPI(
        title="STR Training Backend",
        version="0.1.0",
        description=(
            "Backend for the frontend assessment. Pick a property from the "
            "dashboard, underwrite it, submit, and get graded against the "
            "analyst reference."
        ),
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=[o.strip() for o in config.CORS_ORIGINS.split(",")],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    application.include_router(router)
    return application
