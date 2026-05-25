"""
SophiaTurnRepository — persistence layer for SophiaTurn rows.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.sophia_turn import SophiaTurn


class SophiaTurnRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, turn_id: UUID) -> SophiaTurn | None:
        result = await self._session.execute(
            select(SophiaTurn).where(SophiaTurn.id == turn_id)
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, turn_id: UUID) -> SophiaTurn | None:
        result = await self._session.execute(
            select(SophiaTurn)
            .where(SophiaTurn.id == turn_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, turn_key: str) -> SophiaTurn | None:
        result = await self._session.execute(
            select(SophiaTurn).where(SophiaTurn.turn_key == turn_key)
        )
        return result.scalar_one_or_none()

    async def get_for_session(self, session_id: UUID) -> list[SophiaTurn]:
        result = await self._session.execute(
            select(SophiaTurn)
            .where(SophiaTurn.session_id == session_id)
            .order_by(SophiaTurn.turn_index)
        )
        return list(result.scalars().all())
