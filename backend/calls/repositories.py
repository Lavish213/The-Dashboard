"""Call runtime repositories — session, participant, event."""
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.call_event import CallEvent
from models.call_participant import CallParticipant
from models.call_session import CallSession
from models.enums import CallSessionStatus, ParticipantStatus
from repositories.base import BaseRepository, PageResult


class CallSessionRepository(BaseRepository[CallSession]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, CallSession)

    async def get_for_update(self, session_id: UUID) -> CallSession | None:
        """SELECT FOR UPDATE — holds row lock until transaction end."""
        result = await self.session.execute(
            select(CallSession)
            .where(CallSession.id == session_id, CallSession.deleted_at.is_(None))
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_for_update_or_raise(self, session_id: UUID) -> CallSession:
        from core.exceptions import NotFoundError
        obj = await self.get_for_update(session_id)
        if obj is None:
            raise NotFoundError(CallSession.__tablename__, str(session_id))
        return obj

    async def get_active(self, page: int = 1, page_size: int = 20) -> PageResult[CallSession]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[CallSession.session_status == CallSessionStatus.active],
            order_by=CallSession.started_at.desc(),
        )

    async def get_by_call(self, call_id: UUID) -> list[CallSession]:
        result = await self.session.execute(
            select(CallSession)
            .where(CallSession.call_id == call_id, CallSession.deleted_at.is_(None))
            .order_by(CallSession.created_at.desc())
        )
        return list(result.scalars().all())


class CallParticipantRepository(BaseRepository[CallParticipant]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, CallParticipant)

    async def get_for_update(self, participant_id: UUID) -> CallParticipant | None:
        result = await self.session.execute(
            select(CallParticipant)
            .where(CallParticipant.id == participant_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_for_update_or_raise(self, participant_id: UUID) -> CallParticipant:
        from core.exceptions import NotFoundError
        obj = await self.get_for_update(participant_id)
        if obj is None:
            raise NotFoundError(CallParticipant.__tablename__, str(participant_id))
        return obj

    async def get_by_session(self, session_id: UUID) -> list[CallParticipant]:
        result = await self.session.execute(
            select(CallParticipant)
            .where(CallParticipant.session_id == session_id)
            .order_by(CallParticipant.joined_at.asc())
        )
        return list(result.scalars().all())

    async def get_active_by_session(self, session_id: UUID) -> list[CallParticipant]:
        """Return joined or reconnecting participants only."""
        result = await self.session.execute(
            select(CallParticipant)
            .where(
                CallParticipant.session_id == session_id,
                CallParticipant.participant_status.in_([
                    ParticipantStatus.joined,
                    ParticipantStatus.reconnecting,
                ]),
            )
            .order_by(CallParticipant.joined_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_connection_id(self, connection_id: str) -> CallParticipant | None:
        result = await self.session.execute(
            select(CallParticipant)
            .where(
                CallParticipant.connection_id == connection_id,
                CallParticipant.participant_status.in_([
                    ParticipantStatus.joined,
                    ParticipantStatus.reconnecting,
                ]),
            )
        )
        return result.scalar_one_or_none()

    async def get_stale(self, heartbeat_threshold_seconds: int = 30) -> list[CallParticipant]:
        """Return joined participants whose heartbeat has expired."""
        cutoff = datetime.now(UTC) - timedelta(seconds=heartbeat_threshold_seconds)
        result = await self.session.execute(
            select(CallParticipant)
            .where(
                CallParticipant.participant_status == ParticipantStatus.joined,
                CallParticipant.last_heartbeat_at.is_not(None),
                CallParticipant.last_heartbeat_at < cutoff,
            )
        )
        return list(result.scalars().all())


class CallEventRepository(BaseRepository[CallEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, CallEvent)

    async def next_sequence(self, session_id: UUID) -> int:
        """Return next sequence number (MAX + 1, starting at 0)."""
        result = await self.session.execute(
            select(func.coalesce(func.max(CallEvent.sequence) + 1, 0))
            .where(CallEvent.session_id == session_id)
        )
        return result.scalar_one()

    async def append_event(
        self,
        session_id: UUID,
        event_type: str,
        payload: dict,
    ) -> CallEvent:
        """Append event with auto-incrementing sequence. Never mutated after insert."""
        seq = await self.next_sequence(session_id)
        return await self.create(
            session_id=session_id,
            event_type=event_type,
            sequence=seq,
            payload=payload,
        )

    async def get_by_session(
        self,
        session_id: UUID,
        page: int = 1,
        page_size: int = 100,
    ) -> PageResult[CallEvent]:
        """Paginated sequence-ordered event retrieval."""
        count_q = (
            select(func.count())
            .select_from(CallEvent)
            .where(CallEvent.session_id == session_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()

        q = (
            select(CallEvent)
            .where(CallEvent.session_id == session_id)
            .order_by(CallEvent.sequence.asc(), CallEvent.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.execute(q)).scalars().all())
        return PageResult(items=items, total=total, page=page, page_size=page_size)

    async def get_all_ordered(self, session_id: UUID) -> list[CallEvent]:
        """Full ordered event list — for replay only."""
        result = await self.session.execute(
            select(CallEvent)
            .where(CallEvent.session_id == session_id)
            .order_by(CallEvent.sequence.asc(), CallEvent.id.asc())
        )
        return list(result.scalars().all())

    async def get_after_sequence(
        self,
        session_id: UUID,
        after_sequence: int,
        limit: int = 100,
    ) -> list[CallEvent]:
        """Fetch events after a checkpoint — for reconnect recovery."""
        result = await self.session.execute(
            select(CallEvent)
            .where(
                CallEvent.session_id == session_id,
                CallEvent.sequence > after_sequence,
            )
            .order_by(CallEvent.sequence.asc(), CallEvent.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
