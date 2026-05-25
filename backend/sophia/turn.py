"""
SophiaTurnRuntime — conversation turn lifecycle management.

Turn states:
  pending → running → completed
  running → interrupted
  running → awaiting_approval
  awaiting_approval → running  (approval granted)
  awaiting_approval → interrupted  (approval rejected/expired)
  running/interrupted → cancelled

Increments session.turn_count and session.tokens_used on completion.
Emits SophiaEvents for all lifecycle transitions.

Extended with per-turn signal fields:
  - confidence_delta: change in confidence this turn (-1.0 to +1.0)
  - emotional_signal: detected seller emotional state
  - handoff_recommended: whether this turn triggered handoff recommendation
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from governance.engine import GovernanceEngine
from models.enums import (
    SophiaEventType,
    SophiaInterruptionReason,
    SophiaTurnStatus,
)
from models.sophia_turn import SophiaTurn
from repositories.sophia_event import SophiaEventRepository
from repositories.sophia_session import SophiaSessionRepository
from repositories.sophia_turn import SophiaTurnRepository
from sophia.contracts import SophiaTurnInput, SophiaTurnRecord


class SophiaTurnError(Exception):
    pass


class SophiaTurnRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._turns = SophiaTurnRepository(session)
        self._sessions = SophiaSessionRepository(session)
        self._events = SophiaEventRepository(session)
        self._governance = GovernanceEngine(session)

    async def start(
        self,
        inp: SophiaTurnInput,
    ) -> SophiaTurnRecord:
        if inp.turn_key is not None:
            existing = await self._turns.get_by_key(inp.turn_key)
            if existing is not None:
                return self._to_record(existing)

        await self._governance.check_freeze(
            f"sophia:{inp.session_id}", source_runtime="sophia.turn"
        )

        row = SophiaTurn(
            session_id=inp.session_id,
            turn_index=inp.turn_index,
            status=SophiaTurnStatus.running,
            turn_key=inp.turn_key,
            input_payload=inp.input_payload,
            started_at=datetime.now(UTC),
        )
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            SophiaEventType.turn_started,
            session_id=inp.session_id,
            turn_id=row.id,
            actor_id=inp.actor_id,
            payload={
                "turn_index": inp.turn_index,
                "turn_key": inp.turn_key,
            },
        )
        return self._to_record(row)

    async def complete(
        self,
        turn_id: UUID,
        output_payload: dict,
        tool_calls: list | None = None,
        governance_verdict: dict | None = None,
        tokens_input: int = 0,
        tokens_output: int = 0,
        actor_id: UUID | None = None,
        confidence_delta: float = 0.0,
        emotional_signal: str | None = None,
        handoff_recommended: bool = False,
    ) -> SophiaTurnRecord:
        """Complete a running turn. Updates session token accounting."""
        row = await self._turns.get_for_update(turn_id)
        if row is None:
            raise SophiaTurnError(f"Turn {turn_id} not found")
        if row.status not in (
            SophiaTurnStatus.running,
            SophiaTurnStatus.awaiting_approval,
        ):
            raise SophiaTurnError(
                f"Cannot complete turn {turn_id} in status {row.status}"
            )

        row.status = SophiaTurnStatus.completed
        row.output_payload = output_payload
        row.tool_calls = tool_calls or []
        row.governance_verdict = governance_verdict
        row.tokens_input = tokens_input
        row.tokens_output = tokens_output
        row.completed_at = datetime.now(UTC)
        row.confidence_delta = confidence_delta
        row.emotional_signal = emotional_signal
        row.handoff_recommended = handoff_recommended
        self._session.add(row)
        await self._session.flush()

        session_row = await self._sessions.get_for_update(row.session_id)
        if session_row is not None:
            session_row.tokens_used = session_row.tokens_used + tokens_input + tokens_output
            session_row.turn_count = session_row.turn_count + 1
            self._session.add(session_row)
            await self._session.flush()

        await self._events.append(
            SophiaEventType.turn_completed,
            session_id=row.session_id,
            turn_id=turn_id,
            actor_id=actor_id,
            payload={
                "turn_index": row.turn_index,
                "tokens_input": tokens_input,
                "tokens_output": tokens_output,
                "confidence_delta": confidence_delta,
                "emotional_signal": emotional_signal,
                "handoff_recommended": handoff_recommended,
            },
        )
        return self._to_record(row)

    async def interrupt(
        self,
        turn_id: UUID,
        reason: SophiaInterruptionReason,
        notes: str | None = None,
        actor_id: UUID | None = None,
    ) -> SophiaTurnRecord:
        row = await self._turns.get_for_update(turn_id)
        if row is None:
            raise SophiaTurnError(f"Turn {turn_id} not found")
        if row.status not in (
            SophiaTurnStatus.running,
            SophiaTurnStatus.awaiting_approval,
        ):
            raise SophiaTurnError(
                f"Cannot interrupt turn {turn_id} in status {row.status}"
            )

        row.status = SophiaTurnStatus.interrupted
        row.interruption_reason = reason
        row.interruption_notes = notes
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            SophiaEventType.turn_interrupted,
            session_id=row.session_id,
            turn_id=turn_id,
            actor_id=actor_id,
            payload={"reason": reason.value, "notes": notes},
        )
        return self._to_record(row)

    async def await_approval(
        self,
        turn_id: UUID,
        approval_id: UUID,
        actor_id: UUID | None = None,
    ) -> SophiaTurnRecord:
        row = await self._turns.get_for_update(turn_id)
        if row is None:
            raise SophiaTurnError(f"Turn {turn_id} not found")
        if row.status != SophiaTurnStatus.running:
            raise SophiaTurnError(
                f"Cannot gate approval on turn {turn_id} in status {row.status}"
            )

        row.status = SophiaTurnStatus.awaiting_approval
        row.approval_id = approval_id
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def resume_after_approval(
        self,
        turn_id: UUID,
        actor_id: UUID | None = None,
    ) -> SophiaTurnRecord:
        row = await self._turns.get_for_update(turn_id)
        if row is None:
            raise SophiaTurnError(f"Turn {turn_id} not found")
        if row.status != SophiaTurnStatus.awaiting_approval:
            raise SophiaTurnError(
                f"Turn {turn_id} not awaiting approval (status: {row.status})"
            )

        row.status = SophiaTurnStatus.running
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def cancel(
        self,
        turn_id: UUID,
        actor_id: UUID | None = None,
    ) -> SophiaTurnRecord:
        row = await self._turns.get_for_update(turn_id)
        if row is None:
            raise SophiaTurnError(f"Turn {turn_id} not found")
        if row.status not in (
            SophiaTurnStatus.running,
            SophiaTurnStatus.interrupted,
            SophiaTurnStatus.awaiting_approval,
        ):
            raise SophiaTurnError(
                f"Cannot cancel turn {turn_id} in status {row.status}"
            )

        row.status = SophiaTurnStatus.cancelled
        self._session.add(row)
        await self._session.flush()

        await self._events.append(
            SophiaEventType.turn_cancelled,
            session_id=row.session_id,
            turn_id=turn_id,
            actor_id=actor_id,
            payload={"turn_index": row.turn_index},
        )
        return self._to_record(row)

    async def fail(
        self,
        turn_id: UUID,
        error: str,
        actor_id: UUID | None = None,
    ) -> SophiaTurnRecord:
        row = await self._turns.get_for_update(turn_id)
        if row is None:
            raise SophiaTurnError(f"Turn {turn_id} not found")
        if row.status not in (
            SophiaTurnStatus.running,
            SophiaTurnStatus.awaiting_approval,
        ):
            raise SophiaTurnError(
                f"Cannot fail turn {turn_id} in status {row.status}"
            )

        row.status = SophiaTurnStatus.failed
        row.error = error
        self._session.add(row)
        await self._session.flush()
        return self._to_record(row)

    async def get_turns(self, session_id: UUID) -> list[SophiaTurnRecord]:
        rows = await self._turns.get_for_session(session_id)
        return [self._to_record(r) for r in rows]

    def _to_record(self, row: SophiaTurn) -> SophiaTurnRecord:
        return SophiaTurnRecord(
            turn_id=row.id,
            session_id=row.session_id,
            turn_index=row.turn_index,
            status=row.status,
            input_payload=row.input_payload,
            output_payload=row.output_payload,
            tool_calls=row.tool_calls,
            governance_verdict=row.governance_verdict,
            tokens_input=row.tokens_input,
            tokens_output=row.tokens_output,
            interruption_reason=row.interruption_reason,
            interruption_notes=row.interruption_notes,
            approval_id=row.approval_id,
            confidence_delta=getattr(row, "confidence_delta", 0.0),
            emotional_signal=getattr(row, "emotional_signal", None),
            handoff_recommended=getattr(row, "handoff_recommended", False),
            created_at=row.created_at,
        )