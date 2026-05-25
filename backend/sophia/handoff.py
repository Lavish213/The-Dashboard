"""
SophiaHandoffRuntime — human handoff state management.

Handoff flow:
  1. initiate_warm_transfer() → interrupts turn, builds context packet,
     transitions session → awaiting_handoff, fires handoff events
  2. accept_handoff() → session transitions to handed_off
  3. reject_handoff() / timeout → session returns to active

Emits SophiaEvents at each step.

Extended with:
  - initiate_warm_transfer(): atomic interrupt + context packet + mode switch
  - TransferReason support throughout
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import SophiaEventType, SophiaHandoffStatus, SophiaSessionMode
from repositories.sophia_event import SophiaEventRepository
from sophia.confidence_engine import SophiaConfidenceEngine
from sophia.contracts import (
    HandoffPayload,
    SophiaHandoffRecord,
    SophiaHandoffRequest,
    SophiaInterruption,
    TransferReason,
)
from sophia.context_packet import ContextPacketBuilder
from sophia.interruption import SophiaInterruptionRuntime
from sophia.session import SophiaSessionRuntime


class SophiaHandoffRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._sessions = SophiaSessionRuntime(session)
        self._events = SophiaEventRepository(session)
        self._interruption = SophiaInterruptionRuntime(session)
        self._confidence = SophiaConfidenceEngine(session)
        self._context_builder = ContextPacketBuilder(session)

    async def initiate_warm_transfer(
        self,
        session_id: UUID,
        turn_id: UUID,
        operator_user_id: UUID | None = None,
        transfer_reason: TransferReason = TransferReason.operator_manual,
        initiated_by: UUID | None = None,
    ) -> HandoffPayload:
        """
        Atomic warm transfer initiation:
          1. Interrupt current turn
          2. Build context packet from session history
          3. Transition session mode → HUMAN_TAKEOVER
          4. Transition session status → awaiting_handoff
          5. Emit handoff events
          6. Return HandoffPayload with full context packet

        This is the single entry point for all transfer types.
        """
        await self._interruption.interrupt_turn(
            SophiaInterruption(
                session_id=session_id,
                turn_id=turn_id,
                reason=_transfer_reason_to_interruption(transfer_reason),
                notes=f"Warm transfer initiated: {transfer_reason.value}",
                actor_id=initiated_by,
            )
        )

        context_packet = await self._context_builder.build(
            session_id=session_id,
            transfer_reason=transfer_reason,
        )

        await self._sessions.set_mode(
            session_id=session_id,
            mode=SophiaSessionMode.human_takeover,
            actor_id=initiated_by,
            reason=transfer_reason.value,
        )

        if operator_user_id is not None:
            await self._sessions.request_handoff(
                session_id=session_id,
                handoff_to=operator_user_id,
                reason=transfer_reason.value,
                actor_id=initiated_by,
            )

        await self._events.append(
            SophiaEventType.handoff_requested,
            session_id=session_id,
            actor_id=initiated_by,
            payload={
                "transfer_reason": transfer_reason.value,
                "operator_user_id": str(operator_user_id) if operator_user_id else None,
                "deal_heat": context_packet.deal_heat,
                "trust_score": context_packet.trust_score,
                "confidence_score": context_packet.confidence_score,
            },
        )

        return HandoffPayload(
            session_id=session_id,
            transfer_reason=transfer_reason,
            context_packet=context_packet,
            initiated_by=initiated_by,
            operator_user_id=operator_user_id,
            initiated_at=datetime.now(UTC),
        )

    async def request(
        self,
        request: SophiaHandoffRequest,
    ) -> SophiaHandoffRecord:
        """Request human handoff — session → awaiting_handoff."""
        session_record = await self._sessions.request_handoff(
            session_id=request.session_id,
            handoff_to=request.handoff_to,
            reason=request.reason,
            actor_id=request.requested_by,
        )
        return SophiaHandoffRecord(
            session_id=request.session_id,
            handoff_to=request.handoff_to,
            reason=request.reason,
            status=SophiaHandoffStatus.requested,
            requested_at=session_record.created_at,
        )

    async def accept(
        self,
        session_id: UUID,
        accepted_by: UUID,
    ) -> SophiaHandoffRecord:
        """Accept handoff — session → handed_off."""
        session_record = await self._sessions.accept_handoff(
            session_id=session_id,
            actor_id=accepted_by,
        )
        await self._events.append(
            SophiaEventType.handoff_completed,
            session_id=session_id,
            actor_id=accepted_by,
            payload={"accepted_by": str(accepted_by)},
        )
        return SophiaHandoffRecord(
            session_id=session_id,
            handoff_to=session_record.handoff_to or accepted_by,
            reason=session_record.handoff_reason or "",
            status=SophiaHandoffStatus.accepted,
            requested_at=session_record.created_at,
        )

    async def reject(
        self,
        session_id: UUID,
        rejected_by: UUID,
        reason: str,
    ) -> None:
        """Reject handoff — session returns to active."""
        await self._sessions.resume(
            session_id=session_id,
            actor_id=rejected_by,
        )
        await self._events.append(
            SophiaEventType.session_started,
            session_id=session_id,
            actor_id=rejected_by,
            payload={"action": "handoff_rejected", "reason": reason},
        )


def _transfer_reason_to_interruption(reason: TransferReason):
    from models.enums import SophiaInterruptionReason
    mapping = {
        TransferReason.trust_low: SophiaInterruptionReason.handoff_requested,
        TransferReason.hot_lead: SophiaInterruptionReason.handoff_requested,
        TransferReason.seller_requested: SophiaInterruptionReason.handoff_requested,
        TransferReason.ai_uncertain: SophiaInterruptionReason.handoff_requested,
        TransferReason.negotiation: SophiaInterruptionReason.handoff_requested,
        TransferReason.legal_concern: SophiaInterruptionReason.governance_block,
        TransferReason.operator_manual: SophiaInterruptionReason.handoff_requested,
    }
    return mapping.get(reason, SophiaInterruptionReason.handoff_requested)