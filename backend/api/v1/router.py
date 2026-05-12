from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/ping", tags=["system"])
async def v1_ping() -> dict:
    """V1 API liveness stub."""
    return {"status": "ok"}


# Import and include domain routers
from api.routes import (  # noqa: E402
    approvals,
    audit_timeline,
    calls,
    leads,
    notifications,
    operator_sessions,
    properties,
    transcripts,
    workflows,
)

router.include_router(leads.router, prefix="/leads", tags=["leads"])
router.include_router(properties.router, prefix="/properties", tags=["properties"])
router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
router.include_router(calls.router, prefix="/calls", tags=["calls"])
router.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
router.include_router(operator_sessions.router, prefix="/operator-sessions", tags=["operator-sessions"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(audit_timeline.router, prefix="/audit", tags=["audit"])

from api.routes.realtime import router as realtime_router  # noqa: E402

router.include_router(realtime_router)
