"""
SophiaEventRepository — append-only event log for Sophia.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import SophiaEventType
from models.sophia_event import SophiaEvent


class SophiaEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def append(
        self,
        event_type: SophiaEventType,
        *,
        session_id: UUID | None = None,
        turn_id: UUID | None = None,
        actor_id: UUID | None = None,
        correlation_id: str | None = None,
        payload: dict | None = None,
    ) -> SophiaEvent:
        event = SophiaEvent(
            event_type=event_type,
            session_id=session_id,
            turn_id=turn_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
            payload=payload or {},
        )
        self._session.add(event)
        await self._session.flush()
        return event

    async def get_for_session(self, session_id: UUID) -> list[SophiaEvent]:
        result = await self._session.execute(
            select(SophiaEvent)
            .where(SophiaEvent.session_id == session_id)
            .order_by(SophiaEvent.emitted_at)
        )
        return list(result.scalars().all())

    async def get_for_turn(self, turn_id: UUID) -> list[SophiaEvent]:
        result = await self._session.execute(
            select(SophiaEvent)
            .where(SophiaEvent.turn_id == turn_id)
            .order_by(SophiaEvent.emitted_at)
        )
        return list(result.scalars().all())

    async def get_by_type(
        self,
        event_type: SophiaEventType,
        session_id: UUID | None = None,
    ) -> list[SophiaEvent]:
        q = select(SophiaEvent).where(SophiaEvent.event_type == event_type)
        if session_id is not None:
            q = q.where(SophiaEvent.session_id == session_id)
        q = q.order_by(SophiaEvent.emitted_at)
        result = await self._session.execute(q)
        return list(result.scalars().all())
