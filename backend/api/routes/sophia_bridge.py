from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from security.webhooks import verify_karpathys_secret
from services.voice_ingest import acknowledge, call_sid, find_call, lock_call, replay

router = APIRouter(dependencies=[Depends(verify_karpathys_secret)])
DISPOSITION_ACTIONS = {
    "HOT": {"social_post_type": "social_proof", "email_sequence": "hot"},
    "WARM": {"social_post_type": "education", "email_sequence": "nurture"},
    "COLD": {"social_post_type": None, "email_sequence": "nurture"},
    "DEAD": {"social_post_type": None, "email_sequence": None},
}


@router.post("/disposition-action")
async def handle_disposition_action(body: dict, session: AsyncSession = Depends(get_session)):
    sid = call_sid(body)
    disposition = body.get("disposition")
    if not isinstance(disposition, str) or disposition.upper().strip() not in DISPOSITION_ACTIONS:
        raise HTTPException(422, "A recognized advisory disposition is required")
    disposition = disposition.upper().strip()
    await lock_call(session, sid)
    call = await find_call(session, sid)
    if body.get("lead_id") is not None and body["lead_id"] != (call.metadata_ or {}).get("external_lead_id"):
        raise HTTPException(409, "Disposition lead does not match its provider call")
    existing, fingerprint = replay(call, "disposition-proposal", body)
    if existing:
        return existing
    metadata = dict(call.metadata_ or {})
    metadata["disposition_proposal"] = {"disposition": disposition, "requires_approval": True, "suggested_actions": DISPOSITION_ACTIONS[disposition]}
    call.metadata_ = metadata
    return await acknowledge(session, call, "disposition-proposal", fingerprint, status="pending_approval", actions_taken=[], requires_approval=True)


@router.get("/disposition-actions")
async def list_disposition_actions():
    return {"actions": DISPOSITION_ACTIONS, "advisory_only": True, "requires_approval": True}
