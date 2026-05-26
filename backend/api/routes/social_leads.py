from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.social_lead import SocialLead
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


def _serialize(s: SocialLead) -> dict:
    return {
        "id": str(s.id),
        "full_name": s.full_name,
        "phone": s.phone,
        "platform": s.platform,
        "source_post_id": str(s.source_post_id) if s.source_post_id else None,
        "message": s.message,
        "intent_score": s.intent_score,
        "intent_label": s.intent_label,
        "status": s.status,
        "lead_id": str(s.lead_id) if s.lead_id else None,
        "profile_url": s.profile_url,
        "notes": s.notes,
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat(),
    }


@router.get("")
async def list_social_leads(
    status: str | None = Query(None),
    platform: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(SocialLead)
    if status:
        q = q.where(SocialLead.status == status)
    if platform:
        q = q.where(SocialLead.platform == platform)
    q = q.order_by(SocialLead.created_at.desc())
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


@router.post("")
async def create_social_lead(
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    lead = SocialLead(
        full_name=body.get("full_name"),
        phone=body.get("phone"),
        platform=body.get("platform", "facebook"),
        message=body.get("message"),
        intent_score=body.get("intent_score"),
        intent_label=body.get("intent_label"),
        status=body.get("status", "new"),
        profile_url=body.get("profile_url"),
        notes=body.get("notes"),
    )
    session.add(lead)
    await session.commit()
    return _serialize(lead)


@router.patch("/{social_lead_id}/convert")
async def convert_to_lead(
    social_lead_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from fastapi import HTTPException
    from models.lead import Lead
    from models.enums import LeadSource, LeadStatus

    result = await session.execute(select(SocialLead).where(SocialLead.id == social_lead_id))
    social_lead = result.scalar_one_or_none()
    if not social_lead:
        raise HTTPException(status_code=404, detail="Social lead not found")

    lead = Lead(
        full_name=social_lead.full_name or body.get("full_name", "Unknown"),
        phone=social_lead.phone or body.get("phone"),
        lead_source=LeadSource.organic,
        lead_status=LeadStatus.new,
        ai_score=social_lead.intent_score,
        notes=f"From {social_lead.platform}: {social_lead.message or ''}",
    )
    session.add(lead)
    await session.flush()

    social_lead.lead_id = lead.id
    social_lead.status = "converted"
    session.add(social_lead)
    await session.commit()

    return {
        "status": "ok",
        "lead_id": str(lead.id),
        "social_lead_id": str(social_lead_id),
    }