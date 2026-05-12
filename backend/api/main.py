from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_exception_handlers
from api.routes.health import router as health_router
from api.v1.router import router as v1_router
from config.settings import settings
from middleware.correlation import CorrelationMiddleware
from observability.logging import configure_logging

configure_logging(env=settings.app_env)
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("karpathys.startup", env=settings.app_env, version=settings.app_version)
    _validate_startup()
    yield
    logger.info("karpathys.shutdown")


def _validate_startup() -> None:
    from security.secrets import validate_secrets
    validate_secrets(settings)
    logger.info("karpathys.startup.validated")


app = FastAPI(
    title="Karpathys Platform API",
    version=settings.app_version,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

# Middleware (outermost first)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception handlers
register_exception_handlers(app)

# Routers
app.include_router(health_router)
app.include_router(v1_router)
