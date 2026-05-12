"""
PresenceRuntime — operator/participant presence tracking.

Responsibilities:
- online/offline detection via heartbeat staleness
- stale connection cleanup
- reconnect state restoration
- replay-safe: all state derivable from CallParticipant records

NO notification dispatch. NO intelligence.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from calls.repositories import CallParticipantRepository, CallSessionRepository
from calls.runtime.runtime import CallSessionRuntime
from models.enums import ParticipantStatus

logger = structlog.get_logger(__name__)

# Default heartbeat staleness threshold
DEFAULT_HEARTBEAT_THRESHOLD_SECONDS: int = 30


@dataclass(frozen=True)
class PresenceRecord:
    participant_id: UUID
    session_id: UUID
    user_id: UUID | None
    role: str
    status: ParticipantStatus
    connection_id: str | None
    last_heartbeat_at: datetime | None
    is_online: bool


@dataclass(frozen=True)
class StaleCleanupResult:
    dropped_count: int
    participant_ids: list[UUID]


class PresenceRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = CallSessionRepository(session)
        self._participants = CallParticipantRepository(session)
        self._runtime = CallSessionRuntime(session)

    async def get_presence(self, session_id: UUID) -> list[PresenceRecord]:
        """
        Return current presence state for all participants in a session.
        Replay-safe: derived entirely from CallParticipant records.
        """
        participants = await self._participants.get_by_session(session_id)
        now = datetime.now(UTC)
        threshold = timedelta(seconds=DEFAULT_HEARTBEAT_THRESHOLD_SECONDS)
        records: list[PresenceRecord] = []

        for p in participants:
            is_online = (
                p.participant_status == ParticipantStatus.joined
                and p.last_heartbeat_at is not None
                and (now - p.last_heartbeat_at.replace(tzinfo=UTC)) < threshold
            )
            records.append(PresenceRecord(
                participant_id=p.id,
                session_id=session_id,
                user_id=p.user_id,
                role=p.role,
                status=p.participant_status,
                connection_id=p.connection_id,
                last_heartbeat_at=p.last_heartbeat_at,
                is_online=is_online,
            ))

        return records

    async def cleanup_stale(
        self,
        heartbeat_threshold_seconds: int = DEFAULT_HEARTBEAT_THRESHOLD_SECONDS,
    ) -> StaleCleanupResult:
        """
        Detect and drop participants whose heartbeat has expired.
        Emits dropped events per participant.
        Called by a periodic worker — not on the hot path.
        """
        stale = await self._participants.get_stale(heartbeat_threshold_seconds)
        dropped_ids: list[UUID] = []

        for participant in stale:
            await self._runtime.drop_participant(participant.session_id, participant.id)
            dropped_ids.append(participant.id)
            logger.info(
                "presence.participant_dropped",
                participant_id=str(participant.id),
                session_id=str(participant.session_id),
            )

        return StaleCleanupResult(dropped_count=len(dropped_ids), participant_ids=dropped_ids)

    async def restore_on_reconnect(
        self,
        session_id: UUID,
        participant_id: UUID,
        new_connection_id: str,
    ) -> None:
        """
        Restore presence for a reconnecting participant.
        Delegates to CallSessionRuntime.reconnect().
        """
        await self._runtime.reconnect(session_id, participant_id, new_connection_id)
        logger.info(
            "presence.participant_reconnected",
            participant_id=str(participant_id),
            session_id=str(session_id),
        )

    async def record_heartbeat(self, session_id: UUID, participant_id: UUID) -> None:
        """Update heartbeat timestamp for a participant."""
        await self._runtime.heartbeat(session_id, participant_id)
