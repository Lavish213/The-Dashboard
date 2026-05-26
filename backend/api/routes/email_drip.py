from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.email_drip import EmailDrip
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])

SEQUENCES = {
    "nurture": [
        {"day": 7, "subject": "Still thinking about selling?", "body": "Hey {name}, just checking in. If you're still thinking about your place, we'd love to make you a cash offer. No repairs, no agents, just a simple close."},
        {"day": 30, "subject": "Market update for your area", "body": "Hey {name}, values in Stockton/Lodi have been moving. If you're curious what your place might be worth, reply and I'll get you a number."},
        {"day": 60, "subject": "Still here when you're ready", "body": "Hey {name}, no pressure at all. Just wanted you to know we're still buying in your area when you're ready. Cash, fast, as-is."},
    ],
    "hot": [
        {"day": 1, "subject": "Following up on your property", "body": "Hey {name}, just following up from our conversation. Ready to get you that cash offer — just reply with your address and we'll get moving."},
        {"day": 3, "subject": "Quick question", "body": "Hey {name}, did you get a chance to think it over? We close fast and handle everything. Just say the word."},
        {"day": 7, "subject": "Last follow-up", "body": "Hey {name}, I'll stop bugging you after this but wanted to make one last offer to connect. If timing ever works out, we're here."},
    ],
}


def _serialize(d: EmailDrip) -> dict:
    return {
        "id": str(d.id),
        "lead_id": str(d.lead_id) if d.lead_id else None,
        "email": d.email,
        "full_name": d.full_name,
        "sequence": d.sequence,
        "step": d.step,
        "status": d.status,
        "next_send_at": d.next_send_at.isoformat() if d.next_send_at else None,
        "last_sent_at": d.last_sent_at.isoformat() if d.last_sent_at else None,
        "source": d.source,
        "created_at": d.created_at.isoformat(),
    }


@router.get("")
async def list_drips(
    status: str | None = Query(None),
    sequence: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(EmailDrip)
    if status:
        q = q.where(EmailDrip.status == status)
    if sequence:
        q = q.where(EmailDrip.sequence == sequence)
    q = q.order_by(EmailDrip.created_at.desc())
    total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    return {
        "items": [_serialize(d) for d in result.scalars().all()],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("")
async def create_drip(
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    sequence = body.get("sequence", "nurture")
    steps = SEQUENCES.get(sequence, SEQUENCES["nurture"])
    first_step = steps[0]
    next_send = datetime.now(UTC) + timedelta(days=first_step["day"])

    drip = EmailDrip(
        lead_id=body.get("lead_id"),
        email=body.get("email"),
        full_name=body.get("full_name"),
        sequence=sequence,
        step=0,
        status="active",
        next_send_at=next_send,
        source=body.get("source"),
    )
    session.add(drip)
    await session.commit()
    return _serialize(drip)


@router.patch("/{drip_id}/advance")
async def advance_drip(
    drip_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from fastapi import HTTPException
    result = await session.execute(select(EmailDrip).where(EmailDrip.id == drip_id))
    drip = result.scalar_one_or_none()
    if not drip:
        raise HTTPException(status_code=404, detail="Drip not found")

    steps = SEQUENCES.get(drip.sequence, SEQUENCES["nurture"])
    drip.last_sent_at = datetime.now(UTC)
    drip.step += 1

    if drip.step >= len(steps):
        drip.status = "completed"
        drip.next_send_at = None
    else:
        next_step = steps[drip.step]
        drip.next_send_at = datetime.now(UTC) + timedelta(days=next_step["day"])

    session.add(drip)
    await session.commit()
    return _serialize(drip)


@router.patch("/{drip_id}/pause")
async def pause_drip(
    drip_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from fastapi import HTTPException
    result = await session.execute(select(EmailDrip).where(EmailDrip.id == drip_id))
    drip = result.scalar_one_or_none()
    if not drip:
        raise HTTPException(status_code=404, detail="Drip not found")
    drip.status = "paused"
    session.add(drip)
    await session.commit()
    return {"status": "ok"}


@router.get("/due")
async def get_due_drips(
    session: AsyncSession = Depends(get_session),
) -> dict:
    now = datetime.now(UTC)
    q = select(EmailDrip).where(
        EmailDrip.status == "active",
        EmailDrip.next_send_at <= now,
    ).order_by(EmailDrip.next_send_at)
    result = await session.execute(q)
    due = result.scalars().all()
    return {
        "items": [_serialize(d) for d in due],
        "total": len(due),
        "sequences": SEQUENCES,
    }
