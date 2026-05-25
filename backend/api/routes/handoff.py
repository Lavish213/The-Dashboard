"""
Handoff API routes — warm transfer initiation and context packet delivery.

POST /handoff/initiate          — trigger warm transfer for a session
GET  /handoff/{session_id}/context — fetch context packet for active session
POST /handoff/{session_id}/accept  — accept handoff (operator joined)
POST /handoff/{session_id}/reject  — reject handoff (return to Sophia)
GET  /handoff/{session_id}/signals — live confidence/trust/deal_heat signals
"""
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from security.auth import get_current_active_user
from sophia.confidence_engine import SophiaConfidenceEngine
from sophia.context_packet import ContextPacketBuilder
from sophia.contracts import ContextPacket, HandoffPayload, TransferReason, TurnSignals
from sophia.handoff import SophiaHandoffRuntime
from sophia.shadow_logger import SophiaShadowLogger

router = APIRouter(prefix="/handoff", tags=["handoff"])


class InitiateHandoffRequest(BaseModel):
    session_id: UUID
    turn_id: UUID
    transfer_reason: TransferReason = TransferReason.operator_manual
    operator_user_id: UUID | None = None


class AcceptHandoffRequest(BaseModel):
    accepted_by: UUID


class RejectHandoffRequest(BaseModel):
    rejected_by: UUID
    reason: str


class LogOutcomeRequest(BaseModel):
    outcome: str
    duration_seconds: int
    appointment_set: bool
    notes: str | None = None


@router.post(
    "/initiate",
    response_model=None,
    status_code=status.HTTP_200_OK,
    summary="Initiate warm transfer",
)
async def initiate_handoff(
    body: InitiateHandoffRequest,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """
    Atomically interrupt Sophia, build context packet,
    switch session mode to HUMAN_TAKEOVER, and fire handoff events.
    Returns the full context packet for the operator.
    """
    runtime = SophiaHandoffRuntime(session)
    try:
        payload: HandoffPayload = await runtime.initiate_warm_transfer(
            session_id=body.session_id,
            turn_id=body.turn_id,
            operator_user_id=body.operator_user_id,
            transfer_reason=body.transfer_reason,
            initiated_by=current_user.id,
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    packet = payload.context_packet
    return {
        "session_id": str(payload.session_id),
        "transfer_reason": payload.transfer_reason.value,
        "initiated_at": payload.initiated_at.isoformat(),
        "context_packet": {
            "seller_name": packet.seller_name,
            "address": packet.address,
            "phone": packet.phone,
            "motivation": packet.motivation,
            "timeline": packet.timeline,
            "emotional_state": packet.emotional_state,
            "deal_heat": packet.deal_heat,
            "trust_score": packet.trust_score,
            "confidence_score": packet.confidence_score,
            "transfer_reason": packet.transfer_reason.value,
            "objections_raised": packet.objections_raised,
            "key_moments": packet.key_moments,
            "sophia_summary": packet.sophia_summary,
            "turn_count": packet.turn_count,
            "tokens_used": packet.tokens_used,
            "built_at": packet.built_at.isoformat(),
        },
    }


@router.get(
    "/{session_id}/context",
    status_code=status.HTTP_200_OK,
    summary="Fetch context packet for session",
)
async def get_context_packet(
    session_id: UUID,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Fetch current context packet for any active session."""
    builder = ContextPacketBuilder(session)
    packet: ContextPacket = await builder.build(
        session_id=session_id,
        transfer_reason=TransferReason.operator_manual,
    )
    return {
        "seller_name": packet.seller_name,
        "address": packet.address,
        "phone": packet.phone,
        "motivation": packet.motivation,
        "timeline": packet.timeline,
        "emotional_state": packet.emotional_state,
        "deal_heat": packet.deal_heat,
        "trust_score": packet.trust_score,
        "confidence_score": packet.confidence_score,
        "objections_raised": packet.objections_raised,
        "key_moments": packet.key_moments,
        "sophia_summary": packet.sophia_summary,
        "turn_count": packet.turn_count,
        "tokens_used": packet.tokens_used,
        "built_at": packet.built_at.isoformat(),
    }


@router.get(
    "/{session_id}/signals",
    status_code=status.HTTP_200_OK,
    summary="Live confidence/trust/deal_heat signals",
)
async def get_signals(
    session_id: UUID,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    """Poll current turn signals for a session."""
    engine = SophiaConfidenceEngine(session)
    signals: TurnSignals = await engine.evaluate(session_id)
    return {
        "confidence_score": signals.confidence_score,
        "trust_score": signals.trust_score,
        "deal_heat": signals.deal_heat,
        "handoff_recommended": signals.handoff_recommended,
        "signal_notes": signals.signal_notes,
    }


@router.post(
    "/{session_id}/accept",
    status_code=status.HTTP_200_OK,
    summary="Accept handoff — operator joined",
)
async def accept_handoff(
    session_id: UUID,
    body: AcceptHandoffRequest,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    runtime = SophiaHandoffRuntime(session)
    try:
        record = await runtime.accept(
            session_id=session_id,
            accepted_by=body.accepted_by,
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return {
        "session_id": str(record.session_id),
        "status": record.status.value,
        "handoff_to": str(record.handoff_to),
    }


@router.post(
    "/{session_id}/reject",
    status_code=status.HTTP_200_OK,
    summary="Reject handoff — return to Sophia",
)
async def reject_handoff(
    session_id: UUID,
    body: RejectHandoffRequest,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    runtime = SophiaHandoffRuntime(session)
    try:
        await runtime.reject(
            session_id=session_id,
            rejected_by=body.rejected_by,
            reason=body.reason,
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return {"session_id": str(session_id), "status": "returned_to_ai"}


@router.post(
    "/{session_id}/outcome",
    status_code=status.HTTP_200_OK,
    summary="Log takeover outcome for shadow learning",
)
async def log_outcome(
    session_id: UUID,
    body: LogOutcomeRequest,
    current_user=Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
) -> dict:
    logger = SophiaShadowLogger(session)
    try:
        await logger.log_takeover_outcome(
            session_id=session_id,
            outcome=body.outcome,
            duration_seconds=body.duration_seconds,
            appointment_set=body.appointment_set,
            notes=body.notes,
            actor_id=current_user.id,
        )
        await session.commit()
    except Exception as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    return {"session_id": str(session_id), "logged": True}