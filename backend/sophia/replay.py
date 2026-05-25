"""
SophiaReplayRuntime — deterministic conversation replay foundation.

Reconstructs the ordered event sequence for a session from sophia_events.
No side effects — read-only view of what happened, in emission order.

This is the foundation for: replay debugging, audit review, and future
deterministic re-execution of a session from a known checkpoint.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from repositories.sophia_event import SophiaEventRepository
from sophia.contracts import SophiaReplayFrame


class SophiaReplayRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = SophiaEventRepository(session)

    async def get_frames(self, session_id: UUID) -> list[SophiaReplayFrame]:
        """
        Return ordered replay frames for a session.
        Each frame corresponds to one SophiaEvent in emission order.
        """
        events = await self._events.get_for_session(session_id)
        return [
            SophiaReplayFrame(
                frame_index=idx,
                event_type=event.event_type.value,
                session_id=session_id,
                turn_id=event.turn_id,
                payload=event.payload,
                emitted_at=event.emitted_at,
            )
            for idx, event in enumerate(events)
        ]

    async def get_turn_frames(self, turn_id: UUID) -> list[SophiaReplayFrame]:
        """Return ordered replay frames for a single turn."""
        events = await self._events.get_for_turn(turn_id)
        return [
            SophiaReplayFrame(
                frame_index=idx,
                event_type=event.event_type.value,
                session_id=event.session_id or UUID(int=0),
                turn_id=turn_id,
                payload=event.payload,
                emitted_at=event.emitted_at,
            )
            for idx, event in enumerate(events)
        ]
