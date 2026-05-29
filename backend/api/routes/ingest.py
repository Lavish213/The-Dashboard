from __future__ import annotations

import os
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.call import Call
from models.enums import CallProvider, CallStatus, LeadStatus
from models.lead import Lead

router = APIRouter()

_WEBHOOK_SECRET = os.environ.get("KARPATHYS_WEBHOOK_SECRET", "")


def _verify_secret(x_karpathys_secret: str = Header(default="")) -> None:
    if _WEBHOOK_SECRET and x_karpathys_secret != _WEBHOOK_SECRET:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid secret")


@router.post("/call")
async def ingest_call(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_verify_secret),
) -> dict:
    call_sid = body.get("call_sid", "")
    lead_id = body.get("lead_id")

    existing = await session.execute(
        select(Call).where(Call.provider_call_id == call_sid)
    )
    if existing.scalar_one_or_none():
        return {"status": "ok", "call_id": None, "duplicate": True}

    call = Call(
        provider=CallProvider.signalwire,
        call_status=CallStatus.connected,
        provider_call_id=call_sid,
        lead_id=lead_id,
    )
    session.add(call)
    await session.commit()
    return {"status": "ok", "call_id": str(call.id)}


@router.post("/turn")
async def ingest_turn(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_verify_secret),
) -> dict:
    call_sid = body.get("call_sid", "")
    speaker = body.get("speaker", "unknown")
    text = body.get("text", "")
    turn_index = body.get("turn_index", 0)
    trust_score = body.get("trust_score")
    deal_heat = body.get("deal_heat")

    result = await session.execute(
        select(Call).where(Call.provider_call_id == call_sid)
    )
    call = result.scalar_one_or_none()

    if call:
        from models.sophia_session import SophiaSession
        from models.sophia_turn import SophiaTurn
        from models.enums import SophiaTurnStatus

        sophia_session = None
        if call.lead_id:
            sess_result = await session.execute(
                select(SophiaSession)
                .where(SophiaSession.lead_id == call.lead_id)
                .order_by(SophiaSession.created_at.desc())
                .limit(1)
            )
            sophia_session = sess_result.scalar_one_or_none()

        if sophia_session:
            turn = SophiaTurn(
                session_id=sophia_session.id,
                speaker=speaker,
                text=text,
                turn_index=turn_index,
                turn_status=SophiaTurnStatus.completed,
                confidence_delta=trust_score,
            )
            session.add(turn)
            await session.commit()

    return {
        "status": "ok",
        "call_sid": call_sid,
        "speaker": speaker,
        "turn_index": turn_index,
    }


@router.post("/complete")
async def ingest_complete(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_verify_secret),
) -> dict:
    call_sid = body.get("call_sid", "")
    disposition = body.get("disposition")
    turn_count = body.get("turn_count", 0)

    result = await session.execute(
        select(Call).where(Call.provider_call_id == call_sid)
    )
    call = result.scalar_one_or_none()

    if call:
        call.call_status = CallStatus.completed
        duration_seconds = body.get("duration_seconds")
        if duration_seconds is not None:
            call.duration_seconds = int(duration_seconds)
        session.add(call)

        if disposition and call.lead_id:
            lead_result = await session.execute(
                select(Lead).where(Lead.id == call.lead_id)
            )
            lead = lead_result.scalar_one_or_none()
            if lead:
                if disposition in ("appointment_set", "qualified"):
                    lead.lead_status = LeadStatus.qualified
                elif disposition in ("not_interested", "dead"):
                    lead.lead_status = LeadStatus.dead
                session.add(lead)

        await session.commit()

    return {"status": "ok", "call_sid": call_sid}


@router.post("/ended")
async def ingest_ended(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_verify_secret),
) -> dict:
    call_sid = body.get("call_sid", "")

    result = await session.execute(
        select(Call).where(Call.provider_call_id == call_sid)
    )
    call = result.scalar_one_or_none()

    if call and call.call_status == CallStatus.connected:
        call.call_status = CallStatus.completed
        session.add(call)
        await session.commit()

    return {"status": "ok"}


@router.post("/transcript")
async def ingest_transcript(
    body: dict[str, Any],
    session: AsyncSession = Depends(get_session),
    _: None = Depends(_verify_secret),
) -> dict:
    call_sid = body.get("call_sid", "")
    chunk_count = body.get("chunk_count", 0)
    lead_id = body.get("lead_id")

    result = await session.execute(
        select(Call).where(Call.provider_call_id == call_sid)
    )
    call = result.scalar_one_or_none()

    if call and lead_id:
        from models.transcript import Transcript
        from models.enums import TranscriptStatus, TranscriptSourceType
        transcript = Transcript(
            source_type=TranscriptSourceType.call,
            call_id=call.id,
            lead_id=lead_id,
            transcript_status=TranscriptStatus.completed,
        )
        session.add(transcript)
        await session.commit()

    return {"status": "ok", "call_sid": call_sid, "chunk_count": chunk_count}