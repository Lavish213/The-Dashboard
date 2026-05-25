"""
SophiaCancellationRuntime — cancellation and recovery semantics.

Cancellation:
  - Cancels the active turn (if any) first
  - Then cancels the session
  - Emits cancellation_requested event

Recovery:
  - Re-activates an interrupted session
  - Restores from checkpoint if provided
  - Emits recovery_initiated event
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import SophiaEventType, SophiaTurnStatus
from repositories.sophia_event import SophiaEventRepository
from repositories.sophia_turn import SophiaTurnRepository
from sophia.contracts import SophiaCancellationRequest, SophiaSessionRecord
from sophia.session import SophiaSessionRuntime
from sophia.turn import SophiaTurnRuntime


class SophiaCancellationRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = SophiaSessionRuntime(session)
        self._turns = SophiaTurnRuntime(session)
        self._turn_repo = SophiaTurnRepository(session)
        self._events = SophiaEventRepository(session)

    async def cancel(
        self,
        request: SophiaCancellationRequest,
    ) -> SophiaSessionRecord:
        """
        Cancel session and any active turn.
        Emits cancellation_requested then session_cancelled.
        """
        await self._events.append(
            SophiaEventType.cancellation_requested,
            session_id=request.session_id,
            turn_id=request.turn_id,
            actor_id=request.actor_id,
            payload={"reason": request.reason},
        )

        # Cancel active turn if specified
        if request.turn_id is not None:
            turn_row = await self._turn_repo.get(request.turn_id)
            if turn_row is not None and turn_row.status in (
                SophiaTurnStatus.running,
                SophiaTurnStatus.interrupted,
                SophiaTurnStatus.awaiting_approval,
            ):
                await self._turns.cancel(
                    turn_id=request.turn_id,
                    actor_id=request.actor_id,
                )

        return await self._sessions.cancel(
            session_id=request.session_id,
            reason=request.reason,
            actor_id=request.actor_id,
        )

    async def recover(
        self,
        session_id: UUID,
        checkpoint_state: dict | None = None,
        actor_id: UUID | None = None,
    ) -> SophiaSessionRecord:
        """
        Recover an interrupted session — re-activate and restore checkpoint.
        Emits recovery_initiated event.
        """
        await self._events.append(
            SophiaEventType.recovery_initiated,
            session_id=session_id,
            actor_id=actor_id,
            payload={
                "has_checkpoint": checkpoint_state is not None,
                "checkpoint_turn_index": (
                    checkpoint_state.get("turn_index") if checkpoint_state else None
                ),
            },
        )

        session_record = await self._sessions.resume(
            session_id=session_id,
            actor_id=actor_id,
        )

        # Restore checkpoint state if provided
        if checkpoint_state is not None:
            from repositories.sophia_session import SophiaSessionRepository
            session_row = await SophiaSessionRepository(self._session).get_for_update(session_id)
            if session_row is not None:
                session_row.checkpoint_state = checkpoint_state
                self._session.add(session_row)
                await self._session.flush()

        return session_record
