from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.notification import Notification
from repositories.base import BaseRepository, PageResult


class NotificationRepository(BaseRepository[Notification]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Notification)

    async def get_unread_for_user(self, user_id: UUID, page: int = 1, page_size: int = 20) -> PageResult[Notification]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            ],
            order_by=Notification.created_at.desc(),
        )
