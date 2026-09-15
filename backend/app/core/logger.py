import logging

import structlog

from app.core.config import get_config

logging.basicConfig(level=get_config().log_level, format="%(message)s")

structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.make_filtering_bound_logger(get_config().log_level),
    logger_factory=structlog.PrintLoggerFactory(),
)

logger = structlog.get_logger("strs_training")
