from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.lead import Lead
from models.enums import LeadStatus, LeadSource
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("")
async def list_leads(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    status: LeadStatus | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(Lead)
    if status:
        q = q.where(Lead.lead_status == status)
    q = q.order_by(Lead.created_at.desc())

    total_result = await session.execute(
        select(func.count()).select_from(q.subquery())
    )
    total = total_result.scalar_one()

    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    leads = result.scalars().all()

    return {
        "items": [
            {
                "id": str(l.id),
                "full_name": l.full_name,
                "phone": l.phone,
                "email": l.email,
                "lead_status": l.lead_status.value,
                "lead_source": l.lead_source.value if l.lead_source else None,
                "ai_score": l.ai_score,
                "last_contacted_at": l.last_contacted_at.isoformat() if l.last_contacted_at else None,
                "property_id": str(l.property_id) if l.property_id else None,
                "assigned_user_id": str(l.assigned_user_id) if l.assigned_user_id else None,
                "created_at": l.created_at.isoformat(),
                "updated_at": l.updated_at.isoformat(),
            }
            for l in leads
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }


@router.get("/{lead_id}")
async def get_lead(
    lead_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    lead = await session.get(Lead, lead_id)
    if not lead:
        from fastapi import HTTPException, status
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Lead not found")
    return {
        "id": str(lead.id),
        "full_name": lead.full_name,
        "phone": lead.phone,
        "email": lead.email,
        "lead_status": lead.lead_status.value,
        "lead_source": lead.lead_source.value if lead.lead_source else None,
        "ai_score": lead.ai_score,
        "last_contacted_at": lead.last_contacted_at.isoformat() if lead.last_contacted_at else None,
        "property_id": str(lead.property_id) if lead.property_id else None,
        "assigned_user_id": str(lead.assigned_user_id) if lead.assigned_user_id else None,
        "created_at": lead.created_at.isoformat(),
        "updated_at": lead.updated_at.isoformat(),
    }


@router.patch("/{lead_id}/status")
async def update_lead_status(
    lead_id: UUID,
    status: LeadStatus,
    session: AsyncSession = Depends(get_session),
) -> dict:
    lead = await session.get(Lead, lead_id)
    if not lead:
        from fastapi import HTTPException, status as http_status
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Lead not found")
    lead.lead_status = status
    session.add(lead)
    await session.commit()
    return {"id": str(lead.id), "lead_status": lead.lead_status.value}