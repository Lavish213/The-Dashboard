from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info(
        "karpathys.startup",
        env=settings.app_env,
        version=settings.app_version,
    )
    _validate_startup()
    yield
    logger.info("karpathys.shutdown")


def _validate_startup() -> None:
    """Fail fast on misconfiguration at startup."""
    if settings.is_production and settings.secret_key == "changeme-in-production-use-long-random-string":
        raise RuntimeError("SECRET_KEY must be set in production")
    logger.info("karpathys.startup.validated")


app = FastAPI(
    title="Karpathys Platform API",
    version=settings.app_version,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", tags=["system"])
async def health() -> dict:
    return {
        "status": "ok",
        "env": settings.app_env,
        "version": settings.app_version,
    }
