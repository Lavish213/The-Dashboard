from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification
from repositories.base import BaseRepository, PageResult


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Notification)

    async def get_unread_for_user(self, user_id: UUID, page: int = 1, page_size: int = 20) -> PageResult[Notification]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.deleted_at.is_(None),
            ],
            order_by=Notification.created_at.desc(),
        )

    async def get_for_user(self, user_id: UUID, page: int = 1, page_size: int = 20) -> PageResult[Notification]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[
                Notification.user_id == user_id,
                Notification.deleted_at.is_(None),
            ],
            order_by=Notification.created_at.desc(),
        )

    async def get_unread_count(self, user_id: UUID) -> int:
        return await self.count(
            filters=[
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.deleted_at.is_(None),
            ]
        )

    async def mark_read(self, notification_id: UUID, user_id: UUID) -> Notification | None:
        result = await self.session.execute(
            select(Notification).where(
                Notification.id == notification_id,
                Notification.user_id == user_id,
                Notification.deleted_at.is_(None),
            )
        )
        notif = result.scalar_one_or_none()
        if notif is None:
            return None
        if notif.read_at is None:
            notif.read_at = datetime.now(UTC)
            self.session.add(notif)
            await self.session.flush()
        return notif

    async def mark_all_read(self, user_id: UUID) -> int:
        result = await self.session.execute(
            select(Notification).where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
                Notification.deleted_at.is_(None),
            )
        )
        rows = list(result.scalars().all())
        now = datetime.now(UTC)
        for n in rows:
            n.read_at = now
            self.session.add(n)
        if rows:
            await self.session.flush()
        return len(rows)
