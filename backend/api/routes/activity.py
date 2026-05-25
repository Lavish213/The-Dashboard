from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.domain_event import DomainEventModel as DomainEvent
from security.auth import get_current_active_user

router = APIRouter(dependencies=[Depends(get_current_active_user)])


@router.get("")
async def get_activity(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    event_type: str | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    q = select(DomainEvent)
    if event_type:
        q = q.where(DomainEvent.event_type == event_type)
    q = q.order_by(DomainEvent.occurred_at.desc())
    total = (await session.execute(
        select(func.count()).select_from(q.subquery())
    )).scalar_one()
    result = await session.execute(q.offset((page - 1) * page_size).limit(page_size))
    events = result.scalars().all()
    return {
        "items": [
            {
                "id": str(e.id),
                "event_type": e.event_type,
                "payload": e.payload,
                "occurred_at": e.occurred_at.isoformat(),
            }
            for e in events
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
        "total_pages": max(1, -(-total // page_size)),
    }