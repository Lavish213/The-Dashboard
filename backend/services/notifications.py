"""
NotificationRuntime — append-only notification lifecycle.

Responsibilities:
- create (append-only, no update)
- mark_read / mark_all_read
- paginated feed (all or unread)
- unread count
- realtime push to user:{user_id} WS channel on create

No email. No SMS. No external push providers.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import NotificationType
from models.notification import Notification
from realtime.broadcast import BroadcastService
from realtime.protocol import RealtimeEvent
from repositories.base import PageResult
from repositories.notification import NotificationRepository

logger = structlog.get_logger(__name__)

broadcast_service = BroadcastService()

EVT_NOTIFICATION_CREATED = "notification.created"
EVT_NOTIFICATION_READ = "notification.read"
EVT_NOTIFICATIONS_READ_ALL = "notifications.read_all"


def _user_channel(user_id: UUID) -> str:
    return f"user:{user_id}"


class NotificationRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = NotificationRepository(session)

    async def create(
        self,
        user_id: UUID,
        notification_type: NotificationType,
        title: str,
        body: str,
    ) -> Notification:
        """Append a new notification and push to WS channel."""
        notif = await self._repo.create(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
        )
        logger.info(
            "notification.created",
            notification_id=str(notif.id),
            user_id=str(user_id),
            type=notification_type,
        )
        await broadcast_service.publish(
            RealtimeEvent(
                channel=_user_channel(user_id),
                event_type=EVT_NOTIFICATION_CREATED,
                payload={
                    "notification_id": str(notif.id),
                    "notification_type": notification_type,
                    "title": title,
                },
            )
        )
        return notif

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        notif = await self._repo.mark_read(notification_id, user_id)
        if notif is not None:
            await broadcast_service.publish(
                RealtimeEvent(
                    channel=_user_channel(user_id),
                    event_type=EVT_NOTIFICATION_READ,
                    payload={"notification_id": str(notification_id)},
                )
            )
        return notif

    async def mark_all_read(self, user_id: UUID) -> int:
        count = await self._repo.mark_all_read(user_id)
        if count > 0:
            await broadcast_service.publish(
                RealtimeEvent(
                    channel=_user_channel(user_id),
                    event_type=EVT_NOTIFICATIONS_READ_ALL,
                    payload={"marked_count": count},
                )
            )
        return count

    async def get_feed(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 20,
        unread_only: bool = False,
    ) -> PageResult[Notification]:
        if unread_only:
            return await self._repo.get_unread_for_user(user_id, page=page, page_size=page_size)
        return await self._repo.get_for_user(user_id, page=page, page_size=page_size)

    async def unread_count(self, user_id: UUID) -> int:
        return await self._repo.get_unread_count(user_id)
