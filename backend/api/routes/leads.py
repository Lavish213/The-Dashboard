from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.enums import LeadSource, LeadStatus
from models.lead import Lead
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


def _serialize(lead: Lead) -> dict:
    return {
        "id": str(lead.id),
        "full_name": lead.full_name,
        "phone": lead.phone,
        "email": lead.email,
        "lead_status": lead.lead_status.value,
        "lead_source": lead.lead_source.value if lead.lead_source else None,
        "ai_score": lead.ai_score,
        "notes": lead.notes,
        "follow_up_at": lead.follow_up_at.isoformat() if lead.follow_up_at else None,
        "address": lead.address,
        "city": lead.city,
        "state": lead.state,
        "last_contacted_at": lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
        "property_id": str(lead.property_id) if lead.property_id else None,
        "assigned_user_id": str(lead.assigned_user_id) if lead.assigned_user_id else None,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat(),
    }


@router.get("")
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: LeadStatus | None = None,
    lead_id: UUID | None = Query(None),
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(Lead)
    if status:
        q = q.where(Lead.lead_status == status)
    if lead_id:
        q = q.where(Lead.id == lead_id)
    q = q.order_by(Lead.created_at.desc())
    total_result = await session.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = total_result.scalar_one()
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    leads = result.scalars().all()
    return {
        "items": [_serialize(l) for l in leads],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{lead_id}")
async def get_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return _serialize(lead)


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: UUID,
    status: LeadStatus,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.lead_status = status
    session.add(lead)
    await session.commit()
    return {"status": "ok", "lead_id": str(lead_id), "new_status": status}


@router.post("/{lead_id}/notes")
async def add_lead_note(
    lead_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    existing = lead.notes or ""
    timestamp = datetime.now(UTC).strftime("%Y-%m-%d %H:%M")
    new_note = f"[{timestamp}] {body.get('content', '')}"
    lead.notes = f"{new_note}\n{existing}".strip()
    session.add(lead)
    await session.commit()
    return {
        "id": str(lead_id),
        "content": body.get("content", ""),
        "created_at": datetime.now(UTC).isoformat(),
    }


@router.patch("/{lead_id}/notes")
async def update_lead_notes(
    lead_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.notes = body.get("notes", lead.notes)
    session.add(lead)
    await session.commit()
    return {"status": "ok", "lead_id": str(lead_id)}


@router.patch("/{lead_id}/followup")
async def update_followup(
    lead_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    if body.get("follow_up_at"):
        lead.follow_up_at = datetime.fromisoformat(body["follow_up_at"])
    session.add(lead)
    await session.commit()
    return {"status": "ok", "lead_id": str(lead_id)}


@router.get("/{lead_id}/timeline")
async def get_lead_timeline(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from models.call import Call
    from sqlalchemy import desc

    lead_result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = lead_result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    calls_result = await session.execute(
        select(Call)
        .where(Call.lead_id == lead_id)
        .order_by(desc(Call.created_at))
        .limit(20)
    )
    calls = calls_result.scalars().all()

    events = []

    events.append({
        "type": "created",
        "label": "Lead created",
        "timestamp": lead.created_at.isoformat(),
    })

    for call in calls:
        events.append({
            "type": "call",
            "label": f"Call — {call.call_status}",
            "timestamp": call.created_at.isoformat(),
            "meta": {
                "call_id": str(call.id),
                "duration": call.duration_seconds,
                "status": call.call_status,
            },
        })

    if lead.notes:
        for line in lead.notes.splitlines():
            if line.startswith("["):
                try:
                    ts_end = line.index("]")
                    ts_str = line[1:ts_end]
                    content = line[ts_end + 2:]
                    events.append({
                        "type": "note",
                        "label": content,
                        "timestamp": ts_str,
                    })
                except ValueError:
                    pass

    events.sort(key=lambda e: e["timestamp"], reverse=True)

    return {"lead_id": str(lead_id), "events": events}