import hashlib
import json
from uuid import NAMESPACE_URL, uuid5

from fastapi import HTTPException
from sqlalchemy import func, select

from models.social_lead import SocialLead


async def ingest_message(session, body):
    if not isinstance(body, dict) or len(json.dumps(body)) > 64000:
        raise HTTPException(422, "Bounded provider event required")
    event = body.get("event_id")
    contact, messages = body.get("contact"), body.get("messages")
    if (
        not isinstance(event, str)
        or not 0 < len(event) <= 200
        or not isinstance(contact, dict)
        or not isinstance(messages, list)
        or not 1 <= len(messages) <= 100
    ):
        raise HTTPException(
            422, "Provider event identity, contact and messages required"
        )
    for message in messages:
        if (
            not isinstance(message, dict)
            or not isinstance(message.get("text"), str)
            or not 0 < len(message["text"]) <= 2000
        ):
            raise HTTPException(422, "Invalid provider message")
    for value in contact.values():
        if value is not None and (not isinstance(value, str) or len(value) > 1000):
            raise HTTPException(422, "Invalid contact label")
    identity = uuid5(NAMESPACE_URL, "instantdm:" + event)
    fingerprint = hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    await session.execute(
        select(
            func.pg_advisory_xact_lock(func.hashtextextended("instantdm:" + event, 0))
        )
    )
    existing = await session.scalar(select(SocialLead).where(SocialLead.id == identity))
    if existing:
        if (
            existing.deleted_at is not None
            or (existing.metadata_ or {}).get("source_fingerprint") != fingerprint
        ):
            raise HTTPException(409, "Conflicting or deleted provider event")
        return {
            "status": "ok",
            "social_lead_id": str(identity),
            "duplicate": True,
            "intent_label": None,
            "address_detected": None,
        }
    lead = SocialLead(
        id=identity,
        full_name=contact.get("name") or contact.get("username"),
        phone=contact.get("phone"),
        platform="instagram",
        message=messages[-1]["text"],
        intent_score=None,
        intent_label=None,
        status="new",
        profile_url=contact.get("profile_url") or contact.get("instagram_url"),
        metadata_={
            "source": "instantdm",
            "source_event_id": event,
            "source_fingerprint": fingerprint,
            "property_verified": False,
            "contact_authorized": False,
        },
    )
    session.add(lead)
    await session.commit()
    return {
        "status": "ok",
        "social_lead_id": str(identity),
        "duplicate": False,
        "intent_label": None,
        "address_detected": None,
    }
