from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from config.settings import settings
from db.session import async_session_factory
from observability.metrics import metrics

router = APIRouter(tags=["system"])


@router.get("/api/health")
async def health() -> dict:
    """Liveness probe — returns 200 if the process is running."""
    return {
        "status": "ok",
        "env": settings.app_env,
        "version": settings.app_version,
    }


@router.get("/api/ready")
async def readiness() -> dict:
    """
    Readiness probe — checks DB connectivity.
    Returns 200 if ready, 503 if not.
    """
    try:
        async with async_session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "not_ready", "db": "unreachable", "detail": str(exc)},
        )


@router.get("/api/metrics")
async def runtime_metrics() -> dict:
    """
    Runtime metrics snapshot — uptime, request counts, session stats.
    Not authenticated (internal use). Gate behind network policy in production.
    """
    return metrics.snapshot()
