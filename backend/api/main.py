from __future__ import annotations

import asyncio
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
from middleware.metrics import MetricsMiddleware
from observability.logging import configure_logging

configure_logging(env=settings.app_env)
logger = structlog.get_logger(__name__)

_STALE_CLEANUP_INTERVAL_SECONDS = 60


async def _stale_session_cleanup_loop() -> None:
    """
    Background task: expire operator sessions whose heartbeat has lapsed.
    Runs every STALE_CLEANUP_INTERVAL_SECONDS. Independent DB session per run.
    """
    from db.session import async_session_factory
    from services.operator_sessions import OperatorSessionRuntime

    while True:
        await asyncio.sleep(_STALE_CLEANUP_INTERVAL_SECONDS)
        try:
            async with async_session_factory() as session:
                rt = OperatorSessionRuntime(session)
                result = await rt.cleanup_stale()
                if result.expired_count:
                    logger.info(
                        "operator.session.stale_cleanup",
                        expired=result.expired_count,
                    )
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("operator.session.stale_cleanup.error", error=str(exc))


async def _close_all_websockets() -> None:
    """Gracefully close all active WebSocket connections on shutdown."""
    from realtime.manager import connection_manager

    count = connection_manager.connection_count
    if count == 0:
        return
    logger.info("realtime.shutdown.closing_connections", count=count)
    connection_ids = list(connection_manager._connections.keys())
    for cid in connection_ids:
        await connection_manager.disconnect(cid)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    logger.info("karpathys.startup", env=settings.app_env, version=settings.app_version)
    _validate_startup()

    cleanup_task = asyncio.create_task(_stale_session_cleanup_loop())
    logger.info("karpathys.startup.complete")

    try:
        yield
    finally:
        logger.info("karpathys.shutdown.starting")
        cleanup_task.cancel()
        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass
        await _close_all_websockets()
        logger.info("karpathys.shutdown.complete")


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

# Middleware (outermost → innermost)
app.add_middleware(MetricsMiddleware)
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
