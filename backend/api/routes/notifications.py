"""Notification API routes — append-only feed, read state, WS push."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.enums import NotificationType
from services.notifications import NotificationRuntime

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    user_id: UUID
    notification_type: NotificationType
    title: str
    body: str
    read_at: object | None
    created_at: object


class NotificationCreateBody(BaseModel):
    user_id: UUID
    notification_type: NotificationType
    title: str
    body: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED)
async def create_notification(
    body: NotificationCreateBody,
    session: AsyncSession = Depends(get_session),
) -> NotificationResponse:
    rt = NotificationRuntime(session)
    notif = await rt.create(
        user_id=body.user_id,
        notification_type=body.notification_type,
        title=body.title,
        body=body.body,
    )
    return NotificationResponse.model_validate(notif)


@router.get("", response_model=dict)
async def list_notifications(
    user_id: UUID = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = NotificationRuntime(session)
    result = await rt.get_feed(user_id, page=page, page_size=page_size, unread_only=unread_only)
    return {
        "items": [NotificationResponse.model_validate(n).model_dump() for n in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": result.total_pages,
    }


@router.get("/unread-count", response_model=dict)
async def unread_count(
    user_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = NotificationRuntime(session)
    count = await rt.unread_count(user_id)
    return {"user_id": str(user_id), "unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: UUID,
    user_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
) -> NotificationResponse:
    rt = NotificationRuntime(session)
    notif = await rt.mark_read(notification_id, user_id)
    if notif is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationResponse.model_validate(notif)


@router.post("/read-all", response_model=dict)
async def mark_all_read(
    user_id: UUID = Query(...),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = NotificationRuntime(session)
    count = await rt.mark_all_read(user_id)
    return {"marked_count": count}
