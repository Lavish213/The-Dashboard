from fastapi import APIRouter

router = APIRouter(prefix="/api/v1")


@router.get("/ping", tags=["system"])
async def v1_ping() -> dict:
    return {"status": "ok"}


from api.routes import (
    activity,
    analytics,
    approvals,
    audit_timeline,
    auth,
    calls,
    curator,
    email_drip,
    ingest,
    instantdm_webhook,
    leads,
    notifications,
    operator_sessions,
    properties,
    property_search,
    reddit_monitor,
    referrals,
    social,
    social_leads,
    transcripts,
    workflows,
)
from api.routes import realtime_active

router.include_router(auth.router)
router.include_router(leads.router, prefix="/leads", tags=["leads"])
router.include_router(properties.router, prefix="/properties", tags=["properties"])
router.include_router(workflows.router, prefix="/workflows", tags=["workflows"])
router.include_router(approvals.router, prefix="/approvals", tags=["approvals"])
router.include_router(calls.router, prefix="/calls", tags=["calls"])
router.include_router(transcripts.router, prefix="/transcripts", tags=["transcripts"])
router.include_router(operator_sessions.router, prefix="/operator-sessions", tags=["operator-sessions"])
router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
router.include_router(audit_timeline.router, prefix="/audit", tags=["audit"])
router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
router.include_router(activity.router, prefix="/activity", tags=["activity"])
router.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
router.include_router(property_search.router, prefix="/property-search", tags=["property-search"])
router.include_router(realtime_active.router, prefix="/realtime/active-call", tags=["realtime"])
router.include_router(social.router, prefix="/social/posts", tags=["social"])
router.include_router(social_leads.router, prefix="/social/leads", tags=["social"])
router.include_router(curator.router, prefix="/curator", tags=["curator"])
router.include_router(reddit_monitor.router, prefix="/reddit/matches", tags=["reddit"])
router.include_router(instantdm_webhook.router, prefix="/webhooks", tags=["webhooks"])
router.include_router(email_drip.router, prefix="/email-drip", tags=["email"])
router.include_router(referrals.router, prefix="/referrals", tags=["referrals"])

from api.routes.realtime import router as realtime_router
router.include_router(realtime_router)
