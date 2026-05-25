"""
SophiaSessionRepository — persistence layer for SophiaSession rows.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import SophiaSessionStatus
from models.sophia_session import SophiaSession


class SophiaSessionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get(self, session_id: UUID) -> SophiaSession | None:
        result = await self._session.execute(
            select(SophiaSession).where(SophiaSession.id == session_id)
        )
        return result.scalar_one_or_none()

    async def get_by_key(self, session_key: str) -> SophiaSession | None:
        result = await self._session.execute(
            select(SophiaSession).where(SophiaSession.session_key == session_key)
        )
        return result.scalar_one_or_none()

    async def get_for_update(self, session_id: UUID) -> SophiaSession | None:
        result = await self._session.execute(
            select(SophiaSession)
            .where(SophiaSession.id == session_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_active_for_workflow(self, workflow_id: UUID) -> list[SophiaSession]:
        result = await self._session.execute(
            select(SophiaSession).where(
                SophiaSession.workflow_id == workflow_id,
                SophiaSession.status == SophiaSessionStatus.active,
            )
        )
        return list(result.scalars().all())
