from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.enums import LeadStatus
from models.lead import Lead
from security.permissions import require_permission
from security.rbac import Permission

router = APIRouter(dependencies=[Depends(require_permission(Permission.LEADS_READ))])


class FollowupUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    follow_up_at: datetime | None

    @field_validator("follow_up_at", mode="before")
    @classmethod
    def reject_numeric_date(cls, value):
        if value is not None and not isinstance(value, (str, datetime)):
            raise ValueError("Use an ISO timestamp with a timezone, or null to cancel")
        return value

    @field_validator("follow_up_at")
    @classmethod
    def validate_date(cls, value):
        if value is None:
            return None
        if value.utcoffset() is None:
            raise ValueError("follow_up_at must include a timezone")
        value = value.astimezone(UTC)
        if value <= datetime.now(UTC):
            raise ValueError("follow_up_at must be in the future")
        return value


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
    statuses: list[LeadStatus] | None = Query(None),
    scheduled_only: bool = False,
    follow_up_start: datetime | None = None,
    follow_up_end: datetime | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(Lead).where(Lead.deleted_at.is_(None))
    if status:
        q = q.where(Lead.lead_status == status)
    if lead_id:
        q = q.where(Lead.id == lead_id)
    if statuses:
        q = q.where(Lead.lead_status.in_(statuses))
    for boundary in (follow_up_start, follow_up_end):
        if boundary is not None and boundary.utcoffset() is None:
            raise HTTPException(422, "Follow-up range timestamps must include a timezone")
    if follow_up_start and follow_up_end and follow_up_end <= follow_up_start:
        raise HTTPException(422, "Follow-up range end must be after its start")
    if scheduled_only:
        q = q.where(Lead.follow_up_at.is_not(None))
    if follow_up_start:
        q = q.where(Lead.follow_up_at >= follow_up_start)
    if follow_up_end:
        q = q.where(Lead.follow_up_at < follow_up_end)
    total_result = await session.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = total_result.scalar_one()
    summary = None
    if statuses:
        filtered = q.subquery()
        grouped = await session.execute(select(
            filtered.c.lead_status,
            func.count().label("lead_count"),
            func.sum(func.coalesce(filtered.c.ai_score, 0)).label("score_sum"),
        ).group_by(filtered.c.lead_status))
        rows = grouped.all()
        summary = {
            "by_status": {row.lead_status.value: row.lead_count for row in rows},
            "average_score": round(sum(row.score_sum for row in rows) / total) if total else 0,
            "score_total": sum(row.score_sum for row in rows),
        }
    q = q.order_by(Lead.follow_up_at.asc(), Lead.id.asc()) if scheduled_only else q.order_by(Lead.created_at.desc(), Lead.id.desc())
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    leads = result.scalars().all()
    return {
        "items": [_serialize(lead) for lead in leads],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, (total + page_size - 1) // page_size),
        "summary": summary,
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


@router.patch("/{lead_id}/status", dependencies=[Depends(require_permission(Permission.LEADS_WRITE))])
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


@router.post("/{lead_id}/notes", dependencies=[Depends(require_permission(Permission.LEADS_WRITE))])
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


@router.patch("/{lead_id}/notes", dependencies=[Depends(require_permission(Permission.LEADS_WRITE))])
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


@router.patch("/{lead_id}/followup", dependencies=[Depends(require_permission(Permission.LEADS_WRITE))])
async def update_followup(
    lead_id: UUID,
    body: FollowupUpdate,
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(select(Lead).where(Lead.id == lead_id))
    lead = result.scalar_one_or_none()
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    lead.follow_up_at = body.follow_up_at
    session.add(lead)
    await session.commit()
    return {"status": "ok", "lead_id": str(lead_id), "follow_up_at": lead.follow_up_at.isoformat() if lead.follow_up_at else None}


@router.get("/{lead_id}/timeline")
async def get_lead_timeline(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from sqlalchemy import desc

    from models.call import Call

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
