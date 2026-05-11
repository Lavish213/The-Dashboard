from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import UserStatus
from models.user import User
from repositories.base import BaseRepository, PageResult


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, User)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.session.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    async def get_active_users(self, page: int = 1, page_size: int = 20) -> PageResult[User]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[User.status == UserStatus.active],
            order_by=User.created_at.desc(),
        )
