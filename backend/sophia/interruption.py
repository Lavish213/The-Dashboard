"""
SophiaInterruptionRuntime — interruption handling foundation.

Handles: user barge-in, timeout, governance block, tool approval required,
handoff requested, cancellation, and generic errors.

Interrupting a session stops the active turn and transitions the session
to interrupted status. The caller can resume() or cancel() after.

Extended with:
  - evaluate_and_interrupt(): checks confidence engine before interrupting
  - seller_requested_human(): explicit seller request for human operator
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import SophiaInterruptionReason
from sophia.confidence_engine import SophiaConfidenceEngine
from sophia.contracts import SophiaInterruption, TransferReason, TurnSignals, SophiaTurnRecord
from sophia.session import SophiaSessionRuntime
from sophia.turn import SophiaTurnRuntime


class SophiaInterruptionRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = SophiaSessionRuntime(session)
        self._turns = SophiaTurnRuntime(session)
        self._confidence = SophiaConfidenceEngine(session)

    async def interrupt_turn(
        self,
        interruption: SophiaInterruption,
    ) -> SophiaTurnRecord:
        """
        Interrupt the active turn and update session state.
        Emits turn_interrupted + session interruption event.
        """
        turn_record = await self._turns.interrupt(
            turn_id=interruption.turn_id,
            reason=interruption.reason,
            notes=interruption.notes,
            actor_id=interruption.actor_id,
        )
        await self._sessions.interrupt(
            session_id=interruption.session_id,
            reason=interruption.reason.value,
            actor_id=interruption.actor_id,
        )
        return turn_record

    async def evaluate_and_interrupt(
        self,
        session_id: UUID,
        turn_id: UUID,
        actor_id: UUID | None = None,
    ) -> tuple[SophiaTurnRecord, TurnSignals, TransferReason | None]:
        """
        Evaluate confidence signals then interrupt if handoff recommended.
        Returns the interrupted turn, current signals, and transfer reason.
        Used by the handoff runtime to atomically check + interrupt.
        """
        signals = await self._confidence.evaluate(session_id)
        transfer_reason = await self._confidence.get_transfer_reason(session_id)

        turn_record = await self.interrupt_turn(
            SophiaInterruption(
                session_id=session_id,
                turn_id=turn_id,
                reason=SophiaInterruptionReason.handoff_requested,
                notes=f"Handoff recommended: {', '.join(signals.signal_notes)}",
                actor_id=actor_id,
            )
        )
        return turn_record, signals, transfer_reason

    async def barge_in(
        self,
        session_id: UUID,
        turn_id: UUID,
        actor_id: UUID | None = None,
    ) -> SophiaTurnRecord:
        """User barge-in — interrupt turn immediately."""
        return await self._turns.interrupt(
            turn_id=turn_id,
            reason=SophiaInterruptionReason.user_barge_in,
            notes="User barge-in",
            actor_id=actor_id,
        )

    async def seller_requested_human(
        self,
        session_id: UUID,
        turn_id: UUID,
        actor_id: UUID | None = None,
    ) -> SophiaTurnRecord:
        """
        Seller explicitly asked to speak with a human.
        Interrupts the turn with seller_requested reason.
        """
        return await self.interrupt_turn(
            SophiaInterruption(
                session_id=session_id,
                turn_id=turn_id,
                reason=SophiaInterruptionReason.handoff_requested,
                notes="Seller explicitly requested human operator",
                actor_id=actor_id,
            )
        )

    async def timeout(
        self,
        session_id: UUID,
        turn_id: UUID,
    ) -> SophiaTurnRecord:
        """Interrupt turn due to timeout."""
        return await self.interrupt_turn(
            SophiaInterruption(
                session_id=session_id,
                turn_id=turn_id,
                reason=SophiaInterruptionReason.timeout,
                notes="Turn timeout exceeded",
            )
        )

    async def governance_block(
        self,
        session_id: UUID,
        turn_id: UUID,
        reason: str,
        actor_id: UUID | None = None,
    ) -> SophiaTurnRecord:
        """Interrupt turn because governance policy blocked execution."""
        return await self.interrupt_turn(
            SophiaInterruption(
                session_id=session_id,
                turn_id=turn_id,
                reason=SophiaInterruptionReason.governance_block,
                notes=reason,
                actor_id=actor_id,
            )
        )