from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.call import Call
from models.enums import CallStatus
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("")
async def get_active_call(
    session: AsyncSession = Depends(get_session),
) -> dict:
    result = await session.execute(
        select(Call)
        .where(Call.call_status == CallStatus.connected)
        .order_by(desc(Call.created_at))
        .limit(1)
    )
    call = result.scalar_one_or_none()

    if not call:
        recent_result = await session.execute(
            select(Call)
            .where(Call.call_status == CallStatus.completed)
            .order_by(desc(Call.created_at))
            .limit(5)
        )
        recent = recent_result.scalars().all()
        return {
            "active": None,
            "recent": [
                {
                    "id": str(c.id),
                    "caller_name": None,
                    "duration_seconds": c.duration_seconds,
                    "outcome": None,
                    "cost_usd": None,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                }
                for c in recent
            ],
        }

    recent_result = await session.execute(
        select(Call)
        .where(Call.call_status == CallStatus.completed)
        .order_by(desc(Call.created_at))
        .limit(5)
    )
    recent = recent_result.scalars().all()

    return {
        "active": {
            "session_id": str(call.id),
            "turn_id": str(call.id),
            "caller_name": None,
            "phone": None,
            "duration_seconds": call.duration_seconds or 0,
            "status": call.call_status,
            "provider_call_id": call.provider_call_id,
            "lead_id": str(call.lead_id) if call.lead_id else None,
        },
        "recent": [
            {
                "id": str(c.id),
                "caller_name": None,
                "duration_seconds": c.duration_seconds,
                "outcome": None,
                "cost_usd": None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in recent
        ],
    }
