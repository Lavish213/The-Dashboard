"""
SophiaSessionRuntime — state machine for Sophia conversation sessions.

State transitions:
  initializing → active
  active → interrupted
  active → awaiting_handoff
  active → completed
  active → cancelled
  active → failed
  interrupted → active  (resume)
  interrupted → cancelled
  awaiting_handoff → handed_off
  awaiting_handoff → active  (handoff rejected/timed out)

All transitions emit SophiaEvents. Idempotent on session_key.

Extended with operator mode:
  mode: AI (default) → HUMAN_TAKEOVER
  set_mode() transitions mode and emits mode_changed event.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from governance.engine import GovernanceEngine
from models.enums import SophiaEventType, SophiaSessionMode, SophiaSessionStatus
from models.sophia_session import SophiaSession
from repositories.sophia_event import SophiaEventRepository
from repositories.sophia_session import SophiaSessionRepository
from sophia.contracts import SophiaSessionRecord, SophiaSessionSpec


class SophiaSessionError(Exception):
    pass


_VALID_TRANSITIONS: dict[SophiaSessionStatus, set[SophiaSessionStatus]] = {
    SophiaSessionStatus.initializing: {SophiaSessionStatus.active},
    SophiaSessionStatus.active: {
        SophiaSessionStatus.interrupted,
        SophiaSessionStatus.awaiting_handoff,
        SophiaSessionStatus.completed,
        SophiaSessionStatus.cancelled,
        SophiaSessionStatus.failed,
    },
    SophiaSessionStatus.interrupted: {
        SophiaSessionStatus.active,
        SophiaSessionStatus.cancelled,
    },
    SophiaSessionStatus.awaiting_handoff: {
        SophiaSessionStatus.handed_off,
        SophiaSessionStatus.active,
    },
    SophiaSessionStatus.handed_off: set(),
    SophiaSessionStatus.completed: set(),
    SophiaSessionStatus.cancelled: set(),
    SophiaSessionStatus.failed: set(),
}


class SophiaSessionRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = SophiaSessionRepository(session)
        self._events = SophiaEventRepository(session)
        self._governance = GovernanceEngine(session)

    async def create(self, spec: SophiaSessionSpec) -> SophiaSessionRecord:
        existing = await self._sessions.get_by_key(spec.session_key)
        if existing is not None:
            return self._to_record(existing)

        await self._governance.check_freeze("global", source_runtime="sophia.session")

        row = SophiaSession(
            session_key=spec.session_key,
            status=SophiaSessionStatus.initializing,
            mode=SophiaSessionMode.ai,
            channel=spec.channel,
            workflow_id=spec.workflow_id,
            lead_id=spec.lead_id,
            initiated_by=spec.initiated_by,
            channel_metadata=spec.channel_metadata,
            token_budget=spec.token_budget,
            max_turns=spec.max_turns,
        )
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            SophiaEventType.session_started,
            session_id=row.id,
            actor_id=spec.initiated_by,
            payload={
                "session_key": spec.session_key,
                "channel": spec.channel.value,
                "token_budget": spec.token_budget,
                "max_turns": spec.max_turns,
                "mode": SophiaSessionMode.ai.value,
            },
        )
        return self._to_record(row)

    async def set_mode(
        self,
        session_id: UUID,
        mode: SophiaSessionMode,
        actor_id: UUID | None = None,
        reason: str | None = None,
    ) -> SophiaSessionRecord:
        """Switch session between AI and HUMAN_TAKEOVER modes."""
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")

        previous_mode = getattr(row, "mode", SophiaSessionMode.ai)
        if previous_mode == mode:
            return self._to_record(row)

        row.mode = mode
        if mode == SophiaSessionMode.human_takeover:
            row.taken_over_at = datetime.now(UTC)
            row.taken_over_by = actor_id
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            SophiaEventType.mode_changed,
            session_id=session_id,
            actor_id=actor_id,
            payload={
                "previous_mode": previous_mode.value,
                "new_mode": mode.value,
                "reason": reason,
            },
        )
        return self._to_record(row)

    async def activate(self, session_id: UUID, actor_id: UUID | None = None) -> SophiaSessionRecord:
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")
        self._assert_transition(row.status, SophiaSessionStatus.active)
        row.status = SophiaSessionStatus.active
        row.started_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def interrupt(self, session_id: UUID, reason: str, actor_id: UUID | None = None) -> SophiaSessionRecord:
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")
        self._assert_transition(row.status, SophiaSessionStatus.interrupted)
        row.status = SophiaSessionStatus.interrupted
        self._session.add(row)
        await self._session.flush()
        await self._events.append(
            SophiaEventType.turn_interrupted,
            session_id=session_id,
            actor_id=actor_id,
            payload={"reason": reason},
        )
        return self._to_record(row)

    async def resume(self, session_id: UUID, actor_id: UUID | None = None) -> SophiaSessionRecord:
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")
        self._assert_transition(row.status, SophiaSessionStatus.active)
        row.status = SophiaSessionStatus.active
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def request_handoff(self, session_id: UUID, handoff_to: UUID, reason: str, actor_id: UUID | None = None) -> SophiaSessionRecord:
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")
        self._assert_transition(row.status, SophiaSessionStatus.awaiting_handoff)
        row.status = SophiaSessionStatus.awaiting_handoff
        row.handoff_to = handoff_to
        row.handoff_reason = reason
        self._session.add(row)
        await self._session.flush()
        await self._events.append(
            SophiaEventType.handoff_requested,
            session_id=session_id,
            actor_id=actor_id,
            payload={"handoff_to": str(handoff_to), "reason": reason},
        )
        return self._to_record(row)

    async def accept_handoff(self, session_id: UUID, actor_id: UUID | None = None) -> SophiaSessionRecord:
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")
        self._assert_transition(row.status, SophiaSessionStatus.handed_off)
        row.status = SophiaSessionStatus.handed_off
        row.handed_off_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()
        await self._events.append(
            SophiaEventType.handoff_accepted,
            session_id=session_id,
            actor_id=actor_id,
            payload={"handed_off_at": row.handed_off_at.isoformat()},
        )
        return self._to_record(row)

    async def complete(self, session_id: UUID, actor_id: UUID | None = None) -> SophiaSessionRecord:
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")
        self._assert_transition(row.status, SophiaSessionStatus.completed)
        row.status = SophiaSessionStatus.completed
        row.completed_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()
        await self._events.append(
            SophiaEventType.session_completed,
            session_id=session_id,
            actor_id=actor_id,
            payload={"turn_count": row.turn_count, "tokens_used": row.tokens_used},
        )
        return self._to_record(row)

    async def cancel(self, session_id: UUID, reason: str, actor_id: UUID | None = None) -> SophiaSessionRecord:
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")
        self._assert_transition(row.status, SophiaSessionStatus.cancelled)
        row.status = SophiaSessionStatus.cancelled
        row.cancel_reason = reason
        row.cancelled_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()
        await self._events.append(
            SophiaEventType.session_cancelled,
            session_id=session_id,
            actor_id=actor_id,
            payload={"reason": reason},
        )
        return self._to_record(row)

    async def fail(self, session_id: UUID, error: str, actor_id: UUID | None = None) -> SophiaSessionRecord:
        row = await self._sessions.get_for_update(session_id)
        if row is None:
            raise SophiaSessionError(f"Session {session_id} not found")
        self._assert_transition(row.status, SophiaSessionStatus.failed)
        row.status = SophiaSessionStatus.failed
        row.error = error
        self._session.add(row)
        await self._session.flush()
        await self._events.append(
            SophiaEventType.session_failed,
            session_id=session_id,
            actor_id=actor_id,
            payload={"error": error},
        )
        return self._to_record(row)

    async def get(self, session_id: UUID) -> SophiaSessionRecord | None:
        row = await self._sessions.get(session_id)
        return self._to_record(row) if row else None

    async def get_by_key(self, session_key: str) -> SophiaSessionRecord | None:
        row = await self._sessions.get_by_key(session_key)
        return self._to_record(row) if row else None

    def _assert_transition(self, current: SophiaSessionStatus, target: SophiaSessionStatus) -> None:
        allowed = _VALID_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise SophiaSessionError(
                f"Invalid session transition: {current} → {target}"
            )

    def _to_record(self, row: SophiaSession) -> SophiaSessionRecord:
        return SophiaSessionRecord(
            session_id=row.id,
            session_key=row.session_key,
            status=row.status,
            mode=getattr(row, "mode", SophiaSessionMode.ai),
            channel=row.channel,
            workflow_id=row.workflow_id,
            lead_id=row.lead_id,
            initiated_by=row.initiated_by,
            token_budget=row.token_budget,
            tokens_used=row.tokens_used,
            turn_count=row.turn_count,
            max_turns=row.max_turns,
            channel_metadata=row.channel_metadata,
            checkpoint_state=row.checkpoint_state,
            handoff_to=row.handoff_to,
            handoff_reason=row.handoff_reason,
            taken_over_at=getattr(row, "taken_over_at", None),
            taken_over_by=getattr(row, "taken_over_by", None),
            created_at=row.created_at,
        )