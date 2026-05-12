"""
CallSessionRuntime — realtime call session lifecycle engine.

Responsibilities: create, join, leave, reconnect, heartbeat, complete, fail, replay.
Append-only events. SELECT FOR UPDATE for concurrent safety.
No intelligence. No transcription. No AI.
Calls own realtime state — does NOT touch transcript or workflow state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from calls.repositories import (
    CallEventRepository,
    CallParticipantRepository,
    CallSessionRepository,
)
from calls.runtime.broadcaster import call_broadcaster
from calls.runtime.states import (
    CallSessionTransitionError,
    is_terminal,
    validate_transition,
)
from models.call_event import CallEvent
from models.call_participant import CallParticipant
from models.call_session import CallSession
from models.enums import CallSessionStatus, ParticipantRole, ParticipantStatus

# Event type constants — mirror broadcaster constants for event log
EVT_SESSION_CREATED = "call.session_created"
EVT_SESSION_STARTED = "call.session_started"
EVT_SESSION_COMPLETED = "call.session_completed"
EVT_SESSION_FAILED = "call.session_failed"
EVT_PARTICIPANT_JOINED = "call.participant_joined"
EVT_PARTICIPANT_LEFT = "call.participant_left"
EVT_PARTICIPANT_RECONNECTED = "call.participant_reconnected"
EVT_PARTICIPANT_DROPPED = "call.participant_dropped"
EVT_HEARTBEAT = "call.heartbeat"


@dataclass(frozen=True)
class ReplayResult:
    session_id: UUID
    replayed_events: int
    final_status: CallSessionStatus
    participant_count: int


class CallSessionRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = CallSessionRepository(session)
        self._participants = CallParticipantRepository(session)
        self._events = CallEventRepository(session)

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    async def create_session(self, call_id: UUID | None = None) -> CallSession:
        """Create a new call session in waiting state."""
        call_session = await self._sessions.create(
            call_id=call_id,
            session_status=CallSessionStatus.waiting,
            correlation_id=uuid4(),
        )
        seq = await self._append_event(
            call_session.id,
            EVT_SESSION_CREATED,
            {"call_id": str(call_id) if call_id else None},
        )
        await call_broadcaster.publish_session_created(call_session.id, seq)
        return call_session

    async def complete_session(self, session_id: UUID) -> CallSession:
        """Transition active session to completed."""
        call_session = await self._sessions.get_for_update_or_raise(session_id)
        validate_transition(session_id, call_session.session_status, CallSessionStatus.completed)

        now = datetime.now(UTC)
        call_session.session_status = CallSessionStatus.completed
        call_session.ended_at = now
        self._session.add(call_session)
        await self._session.flush()

        seq = await self._append_event(call_session.id, EVT_SESSION_COMPLETED, {})
        await call_broadcaster.publish_session_completed(call_session.id, seq)
        return call_session

    async def fail_session(self, session_id: UUID, reason: str) -> CallSession:
        """Transition session to failed."""
        call_session = await self._sessions.get_for_update_or_raise(session_id)
        validate_transition(session_id, call_session.session_status, CallSessionStatus.failed)

        call_session.session_status = CallSessionStatus.failed
        call_session.ended_at = datetime.now(UTC)
        self._session.add(call_session)
        await self._session.flush()

        seq = await self._append_event(
            call_session.id, EVT_SESSION_FAILED, {"reason": reason}
        )
        await call_broadcaster.publish_session_failed(call_session.id, reason, seq)
        return call_session

    # ------------------------------------------------------------------
    # Participant lifecycle
    # ------------------------------------------------------------------

    async def join(
        self,
        session_id: UUID,
        role: ParticipantRole,
        user_id: UUID | None = None,
        connection_id: str | None = None,
    ) -> tuple[CallSession, CallParticipant]:
        """
        Join a participant to a session.
        Transitions waiting -> active on first join.
        Returns (session, participant).
        """
        call_session = await self._sessions.get_for_update_or_raise(session_id)

        if is_terminal(call_session.session_status):
            raise CallSessionTransitionError(
                session_id,
                call_session.session_status,
                call_session.session_status,
                reason="session is terminal",
            )

        # Activate session on first join
        if call_session.session_status == CallSessionStatus.waiting:
            call_session.session_status = CallSessionStatus.active
            call_session.started_at = datetime.now(UTC)
            self._session.add(call_session)
            await self._session.flush()
            seq = await self._append_event(call_session.id, EVT_SESSION_STARTED, {})
            await call_broadcaster.publish_session_started(call_session.id, seq)

        participant = await self._participants.create(
            session_id=session_id,
            user_id=user_id,
            role=role,
            participant_status=ParticipantStatus.joined,
            connection_id=connection_id,
            joined_at=datetime.now(UTC),
            last_heartbeat_at=datetime.now(UTC),
        )

        seq = await self._append_event(
            session_id,
            EVT_PARTICIPANT_JOINED,
            {
                "participant_id": str(participant.id),
                "role": role,
                "user_id": str(user_id) if user_id else None,
            },
        )
        await call_broadcaster.publish_participant_joined(
            call_session.id, participant.id, role, seq
        )

        return call_session, participant

    async def leave(self, session_id: UUID, participant_id: UUID) -> CallParticipant:
        """Mark participant as left."""
        participant = await self._participants.get_for_update_or_raise(participant_id)

        participant.participant_status = ParticipantStatus.left
        participant.left_at = datetime.now(UTC)
        participant.connection_id = None
        self._session.add(participant)
        await self._session.flush()

        seq = await self._append_event(
            session_id,
            EVT_PARTICIPANT_LEFT,
            {"participant_id": str(participant_id)},
        )
        await call_broadcaster.publish_participant_left(session_id, participant_id, seq)
        return participant

    async def reconnect(
        self,
        session_id: UUID,
        participant_id: UUID,
        connection_id: str,
    ) -> CallParticipant:
        """
        Restore a reconnecting participant.
        Must be in reconnecting or dropped status.
        """
        participant = await self._participants.get_for_update_or_raise(participant_id)

        if participant.participant_status not in (
            ParticipantStatus.reconnecting,
            ParticipantStatus.dropped,
        ):
            raise ValueError(
                f"Participant {participant_id} is {participant.participant_status}, cannot reconnect"
            )

        participant.participant_status = ParticipantStatus.joined
        participant.connection_id = connection_id
        participant.last_heartbeat_at = datetime.now(UTC)
        self._session.add(participant)
        await self._session.flush()

        seq = await self._append_event(
            session_id,
            EVT_PARTICIPANT_RECONNECTED,
            {"participant_id": str(participant_id), "connection_id": connection_id},
        )
        await call_broadcaster.publish_participant_reconnected(session_id, participant_id, seq)
        return participant

    async def heartbeat(self, session_id: UUID, participant_id: UUID) -> CallParticipant:
        """Update last_heartbeat_at for a participant."""
        participant = await self._participants.get_for_update_or_raise(participant_id)
        participant.last_heartbeat_at = datetime.now(UTC)
        self._session.add(participant)
        await self._session.flush()
        return participant

    async def drop_participant(self, session_id: UUID, participant_id: UUID) -> CallParticipant:
        """Mark a participant as dropped (stale connection cleanup)."""
        participant = await self._participants.get_for_update_or_raise(participant_id)
        participant.participant_status = ParticipantStatus.dropped
        participant.connection_id = None
        self._session.add(participant)
        await self._session.flush()

        seq = await self._append_event(
            session_id,
            EVT_PARTICIPANT_DROPPED,
            {"participant_id": str(participant_id)},
        )
        await call_broadcaster.publish_participant_dropped(session_id, participant_id, seq)
        return participant

    # ------------------------------------------------------------------
    # Replay
    # ------------------------------------------------------------------

    async def replay(self, session_id: UUID) -> ReplayResult:
        """
        Replay all events for a session in sequence order.
        Returns summary — does NOT re-emit events to websocket.
        """
        call_session = await self._sessions.get_by_id_or_raise(session_id)
        events = await self._events.get_all_ordered(session_id)
        active_participants = await self._participants.get_active_by_session(session_id)

        return ReplayResult(
            session_id=session_id,
            replayed_events=len(events),
            final_status=call_session.session_status,
            participant_count=len(active_participants),
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    async def _append_event(
        self,
        session_id: UUID,
        event_type: str,
        payload: dict,
    ) -> int:
        """Append event and return sequence number."""
        event: CallEvent = await self._events.append_event(session_id, event_type, payload)
        return event.sequence
