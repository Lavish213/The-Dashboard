"""Notification API routes — append-only feed, read state, WS push."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.enums import NotificationType
from models.user import User
from security.auth import get_current_active_user
from security.permissions import require_admin
from security.rbac import Permission, has_permission
from services.notifications import NotificationRuntime

router = APIRouter(dependencies=[Depends(get_current_active_user)])


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
    model_config = ConfigDict(extra="forbid")
    user_id: UUID
    notification_type: NotificationType
    title: str = Field(min_length=1, max_length=200)
    body: str = Field(min_length=1, max_length=5000)


def notification_owner(
    user_id: UUID | None = Query(None),
    user: User = Depends(get_current_active_user),
) -> UUID:
    if user_id is not None and user_id != user.id and not has_permission(user.role, Permission.USERS_MANAGE):
        raise HTTPException(403, "Notifications belong to another account")
    return user_id or user.id


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", response_model=NotificationResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
async def create_notification(
    body: NotificationCreateBody,
    session: AsyncSession = Depends(get_session),
) -> NotificationResponse:
    target = await session.scalar(select(User.id).where(User.id == body.user_id))
    if target is None:
        raise HTTPException(404, "Notification recipient not found")
    rt = NotificationRuntime(session, commit_before_publish=True)
    notif = await rt.create(
        user_id=body.user_id,
        notification_type=body.notification_type,
        title=body.title,
        body=body.body,
    )
    return NotificationResponse.model_validate(notif)


@router.get("", response_model=dict)
async def list_notifications(
    user_id: UUID = Depends(notification_owner),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    unread_only: bool = Query(False),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = NotificationRuntime(session, commit_before_publish=True)
    result = await rt.get_feed(user_id, page=page, page_size=page_size, unread_only=unread_only)
    return {
        "items": [NotificationResponse.model_validate(n).model_dump() for n in result.items],
        "total": result.total,
        "page": result.page,
        "page_size": result.page_size,
        "total_pages": max(1, result.total_pages),
    }


@router.get("/unread-count", response_model=dict)
async def unread_count(
    user_id: UUID = Depends(notification_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = NotificationRuntime(session, commit_before_publish=True)
    count = await rt.unread_count(user_id)
    return {"user_id": str(user_id), "unread_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_read(
    notification_id: UUID,
    user_id: UUID = Depends(notification_owner),
    session: AsyncSession = Depends(get_session),
) -> NotificationResponse:
    rt = NotificationRuntime(session, commit_before_publish=True)
    notif = await rt.mark_read(notification_id, user_id)
    if notif is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notification not found")
    return NotificationResponse.model_validate(notif)


@router.post("/read-all", response_model=dict)
async def mark_all_read(
    user_id: UUID = Depends(notification_owner),
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = NotificationRuntime(session, commit_before_publish=True)
    count = await rt.mark_all_read(user_id)
    return {"marked_count": count}
