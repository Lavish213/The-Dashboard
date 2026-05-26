from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session

router = APIRouter()


@router.post("/instantdm")
async def instantdm_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict:
    try:
        body = await request.json()
    except Exception:
        body = {}

    contact = body.get("contact", {})
    messages = body.get("messages", [])

    full_name = contact.get("name") or contact.get("username") or None
    phone = contact.get("phone") or None
    profile_url = contact.get("profile_url") or contact.get("instagram_url") or None

    last_message = None
    address_found = None
    if messages:
        last_message = messages[-1].get("text", "") if isinstance(messages[-1], dict) else str(messages[-1])
        for msg in messages:
            text = msg.get("text", "") if isinstance(msg, dict) else str(msg)
            if any(c.isdigit() for c in text) and len(text) > 8:
                address_found = text.strip()

    intent_score = 8 if address_found else 6
    intent_label = "hot" if address_found else "warm"

    from models.social_lead import SocialLead

    lead = SocialLead(
        full_name=full_name,
        phone=phone,
        platform="instagram",
        message=last_message,
        intent_score=intent_score,
        intent_label=intent_label,
        status="new",
        profile_url=profile_url,
        notes=f"address_detected: {address_found}" if address_found else None,
    )
    session.add(lead)
    await session.commit()

    return {
        "status": "ok",
        "social_lead_id": str(lead.id),
        "intent_label": intent_label,
        "address_detected": address_found,
    }


@router.get("/instantdm/verify")
async def instantdm_verify() -> dict:
    return {"status": "ok"}
