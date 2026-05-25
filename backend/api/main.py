from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.errors import register_exception_handlers
from api.routes.handoff import router as handoff_router
from api.routes.health import router as health_router
from api.v1.router import router as v1_router
from config.settings import settings
from core.redis import close_redis, init_redis
from middleware.correlation import CorrelationMiddleware
from middleware.metrics import MetricsMiddleware
from observability.logging import configure_logging

configure_logging(env=settings.app_env)
logger = structlog.get_logger(__name__)

_STALE_CLEANUP_INTERVAL_SECONDS = 60
_STALE_WS_EVICTION_INTERVAL_SECONDS = 60


async def _approval_expiry_loop() -> None:
    from approvals.expiry import ApprovalExpiryRuntime
    from db.session import async_session_factory

    while True:
        await asyncio.sleep(_STALE_CLEANUP_INTERVAL_SECONDS)
        try:
            async with async_session_factory() as session:
                runtime = ApprovalExpiryRuntime(session)
                result = await runtime.expire_pending()
                if result.expired_count:
                    logger.info("approval.expiry.ran", expired=result.expired_count)
                await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("approval.expiry.error", error=str(exc))


async def _stale_ws_eviction_loop() -> None:
    from realtime.manager import connection_manager
    from realtime.reconnect import heartbeat_tracker
    from realtime.subscriptions import subscription_manager

    while True:
        await asyncio.sleep(_STALE_WS_EVICTION_INTERVAL_SECONDS)
        try:
            stale = heartbeat_tracker.stale_connections()
            for cid in stale:
                subscription_manager.unsubscribe_all(cid)
                heartbeat_tracker.record_disconnect(cid)
                await connection_manager.close_connection(cid)
            if stale:
                logger.info("realtime.stale.evicted", count=len(stale))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("realtime.stale.eviction_error", error=str(exc))


async def _stale_session_cleanup_loop() -> None:
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

    await init_redis()

    cleanup_task = asyncio.create_task(_stale_session_cleanup_loop())
    approval_expiry_task = asyncio.create_task(_approval_expiry_loop())
    ws_eviction_task = asyncio.create_task(_stale_ws_eviction_loop())
    logger.info("karpathys.startup.complete")

    try:
        yield
    finally:
        logger.info("karpathys.shutdown.starting")
        for task in (cleanup_task, approval_expiry_task, ws_eviction_task):
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        await _close_all_websockets()
        await close_redis()
        logger.info("karpathys.shutdown.complete")


def _validate_startup() -> None:
    from security.secrets import validate_secrets
    validate_secrets(settings)
    if settings.is_secret_key_insecure and settings.is_production:
        raise RuntimeError("Insecure secret_key detected in production — aborting startup")
    logger.info("karpathys.startup.validated")


app = FastAPI(
    title="Karpathys Platform API",
    version=settings.app_version,
    docs_url="/api/docs" if not settings.is_production else None,
    redoc_url="/api/redoc" if not settings.is_production else None,
    lifespan=lifespan,
)

app.add_middleware(MetricsMiddleware)
app.add_middleware(CorrelationMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(health_router)
app.include_router(handoff_router, prefix="/api")
app.include_router(v1_router)