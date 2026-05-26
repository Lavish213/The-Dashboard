from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.referral import Referral
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


def _serialize(r: Referral) -> dict:
    return {
        "id": str(r.id),
        "referrer_name": r.referrer_name,
        "referrer_type": r.referrer_type,
        "referrer_phone": r.referrer_phone,
        "referrer_email": r.referrer_email,
        "lead_id": str(r.lead_id) if r.lead_id else None,
        "fee_amount": r.fee_amount,
        "fee_status": r.fee_status,
        "notes": r.notes,
        "created_at": r.created_at.isoformat(),
    }


@router.get("")
async def list_referrals(
    fee_status: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(Referral)
    if fee_status:
        q = q.where(Referral.fee_status == fee_status)
    q = q.order_by(Referral.created_at.desc())
    total = (await session.execute(select(func.count()).select_from(q.subquery()))).scalar_one()
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await session.execute(q)
    return {
        "items": [_serialize(r) for r in result.scalars().all()],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.post("")
async def create_referral(
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    ref = Referral(
        referrer_name=body.get("referrer_name", "Unknown"),
        referrer_type=body.get("referrer_type"),
        referrer_phone=body.get("referrer_phone"),
        referrer_email=body.get("referrer_email"),
        lead_id=body.get("lead_id"),
        fee_amount=body.get("fee_amount"),
        fee_status=body.get("fee_status", "pending"),
        notes=body.get("notes"),
    )
    session.add(ref)
    await session.commit()
    return _serialize(ref)


@router.patch("/{referral_id}/fee")
async def update_fee_status(
    referral_id: UUID,
    body: dict,
    session: AsyncSession = Depends(get_session),
) -> dict:
    from fastapi import HTTPException
    result = await session.execute(select(Referral).where(Referral.id == referral_id))
    ref = result.scalar_one_or_none()
    if not ref:
        raise HTTPException(status_code=404, detail="Referral not found")
    ref.fee_status = body.get("fee_status", ref.fee_status)
    ref.fee_amount = body.get("fee_amount", ref.fee_amount)
    session.add(ref)
    await session.commit()
    return _serialize(ref)


@router.get("/summary")
async def referral_summary(
    session: AsyncSession = Depends(get_session),
) -> dict:
    total_result = await session.execute(select(func.count()).select_from(Referral))
    total = total_result.scalar_one()

    pending_result = await session.execute(
        select(func.count()).select_from(Referral).where(Referral.fee_status == "pending")
    )
    pending = pending_result.scalar_one()

    paid_result = await session.execute(
        select(func.sum(Referral.fee_amount)).select_from(Referral).where(Referral.fee_status == "paid")
    )
    paid_total = paid_result.scalar_one() or 0

    owed_result = await session.execute(
        select(func.sum(Referral.fee_amount)).select_from(Referral).where(Referral.fee_status == "pending")
    )
    owed_total = owed_result.scalar_one() or 0

    return {
        "total_referrals": total,
        "pending_fees": pending,
        "total_paid_out": paid_total,
        "total_owed": owed_total,
    }
