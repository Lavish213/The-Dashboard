from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.session import get_session
import os as _os

from fastapi import Header, HTTPException, status

_WEBHOOK_SECRET = _os.environ.get("KARPATHYS_WEBHOOK_SECRET", "")


def _verify_secret(x_karpathys_secret: str = Header(default="")) -> None:
    if _WEBHOOK_SECRET and x_karpathys_secret != _WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")


router = APIRouter(dependencies=[Depends(_verify_secret)])

DISPOSITION_ACTIONS = {
    "HOT": {
        "social_post_type": "social_proof",
        "email_sequence": "hot",
        "description": "Sophia marked HOT — queue social proof post + hot email sequence",
    },
    "WARM": {
        "social_post_type": "education",
        "email_sequence": "nurture",
        "description": "Sophia marked WARM — queue educational post + nurture sequence",
    },
    "COLD": {
        "social_post_type": None,
        "email_sequence": "nurture",
        "description": "Sophia marked COLD — nurture email only",
    },
    "DEAD": {
        "social_post_type": None,
        "email_sequence": None,
        "description": "Sophia marked DEAD — no follow-up actions",
    },
}


@router.post("/disposition-action")
async def handle_disposition_action(
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from models.lead import Lead
    from models.email_drip import EmailDrip
    from models.social_post import SocialPost
    from datetime import UTC, datetime, timedelta

    lead_id = body.get("lead_id")
    disposition = (body.get("disposition") or "").upper().strip()
    call_sid = body.get("call_sid")
    full_name = body.get("full_name", "")
    phone = body.get("phone", "")

    if not disposition or disposition not in DISPOSITION_ACTIONS:
        return {"status": "skipped", "reason": f"unknown disposition: {disposition}"}

    action = DISPOSITION_ACTIONS[disposition]
    actions_taken = []

    if lead_id:
        lead_result = await session.execute(select(Lead).where(Lead.id == lead_id))
        lead = lead_result.scalar_one_or_none()
        if lead:
            full_name = full_name or lead.full_name or ""
            phone = phone or lead.phone or ""

    if action["email_sequence"] and (phone or full_name):
        steps_map = {"hot": [1, 3, 7], "nurture": [7, 30, 60]}
        days = steps_map.get(action["email_sequence"], [7])[0]
        drip = EmailDrip(
            lead_id=lead_id,
            full_name=full_name,
            sequence=action["email_sequence"],
            step=0,
            status="active",
            next_send_at=datetime.now(UTC) + timedelta(days=days),
            source=f"sophia_call:{call_sid or 'unknown'}",
        )
        session.add(drip)
        actions_taken.append(f"email_drip:{action['email_sequence']}")

    if action["social_post_type"] and full_name:
        first_name = full_name.split()[0] if full_name else "a seller"
        content_map = {
            "social_proof": f"just had a great conversation with a homeowner in the 209 today. if you're thinking about selling, we make it simple — cash, fast, as-is. DM me 🏡",
            "education": f"a lot of homeowners don't realize you can sell without making repairs or hiring an agent. we handle everything. reach out if you're curious what your place is worth.",
        }
        content = content_map.get(action["social_post_type"], "")
        if content:
            post = SocialPost(
                platform="facebook",
                content=content,
                status="draft",
                post_type=action["social_post_type"],
                source_url=f"sophia_disposition:{disposition}",
            )
            session.add(post)
            actions_taken.append(f"social_post:{action['social_post_type']}")

    await session.commit()

    return {
        "status": "ok",
        "disposition": disposition,
        "lead_id": str(lead_id) if lead_id else None,
        "call_sid": call_sid,
        "actions_taken": actions_taken,
        "description": action["description"],
    }


@router.get("/disposition-actions")
async def list_disposition_actions() -> dict:
    return {"actions": DISPOSITION_ACTIONS}
