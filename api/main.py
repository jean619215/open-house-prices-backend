"""FastAPI application factory and startup configuration.

Mounts all routers and configures middleware for the Open House Prices API.
"""

import logging
import logging.config

from fastapi import FastAPI

from api.routers import health

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        FastAPI: The configured application instance.
    """
    application = FastAPI(
        title="Open House Prices API",
        description="台灣房地產實價登錄資料 API",
        version="0.1.0",
    )

    # Routers
    application.include_router(health.router)

    logger.info("FastAPI application created")
    return application


app = create_app()
