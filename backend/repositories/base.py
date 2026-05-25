import math
from datetime import UTC
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from db.base import Base

ModelT = TypeVar("ModelT", bound=Base)

class PageResult(Generic[ModelT]):  # noqa: UP046
    def __init__(self, items: list[ModelT], total: int, page: int, page_size: int):
        self.items = items
        self.total = total
        self.page = page
        self.page_size = page_size
        self.total_pages = math.ceil(total / page_size) if page_size else 0

class BaseRepository(Generic[ModelT]):  # noqa: UP046
    def __init__(self, session: AsyncSession, model: type[ModelT]):
        self.session = session
        self.model = model

    async def get_by_id(self, id: UUID) -> ModelT | None:
        """Fetch by PK. Returns None if not found or soft-deleted."""
        result = await self.session.execute(
            select(self.model).where(
                self.model.id == id,
                # Only filter deleted_at if the model has it
                *([self.model.deleted_at.is_(None)] if hasattr(self.model, 'deleted_at') else [])
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, id: UUID) -> ModelT:
        """Fetch by PK. Raises NotFoundError if missing."""
        from core.exceptions import NotFoundError
        obj = await self.get_by_id(id)
        if obj is None:
            raise NotFoundError(self.model.__tablename__, str(id))
        return obj

    async def create(self, **kwargs) -> ModelT:
        obj = self.model(**kwargs)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def update(self, obj: ModelT, **kwargs) -> ModelT:
        for key, value in kwargs.items():
            setattr(obj, key, value)
        self.session.add(obj)
        await self.session.flush()
        await self.session.refresh(obj)
        return obj

    async def soft_delete(self, obj: ModelT) -> ModelT:
        from datetime import datetime
        if not hasattr(obj, 'deleted_at'):
            raise ValueError(f"{self.model.__name__} does not support soft delete")
        obj.deleted_at = datetime.now(UTC)
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def hard_delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        filters: list[Any] | None = None,
        order_by=None,
    ) -> PageResult[ModelT]:
        """Paginated list with optional filters. Excludes soft-deleted by default."""
        base_filters = []
        if hasattr(self.model, 'deleted_at'):
            base_filters.append(self.model.deleted_at.is_(None))
        if filters:
            base_filters.extend(filters)

        count_q = select(func.count()).select_from(self.model)
        if base_filters:
            count_q = count_q.where(and_(*base_filters))
        total = (await self.session.execute(count_q)).scalar_one()

        q = select(self.model)
        if base_filters:
            q = q.where(and_(*base_filters))
        if order_by is not None:
            q = q.order_by(order_by)
        else:
            if hasattr(self.model, 'created_at'):
                q = q.order_by(self.model.created_at.desc())
        q = q.offset((page - 1) * page_size).limit(page_size)
        items = list((await self.session.execute(q)).scalars().all())
        return PageResult(items=items, total=total, page=page, page_size=page_size)

    async def count(self, filters: list[Any] | None = None) -> int:
        base_filters = []
        if hasattr(self.model, 'deleted_at'):
            base_filters.append(self.model.deleted_at.is_(None))
        if filters:
            base_filters.extend(filters)
        q = select(func.count()).select_from(self.model)
        if base_filters:
            q = q.where(and_(*base_filters))
        return (await self.session.execute(q)).scalar_one()
