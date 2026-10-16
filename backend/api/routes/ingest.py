from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from models.call import Call
from models.enums import (
    CallProvider,
    CallStatus,
    SophiaSessionStatus,
    SophiaTurnStatus,
    TranscriptSourceType,
    TranscriptStatus,
)
from models.sophia_turn import SophiaTurn
from models.transcript import Transcript
from models.transcript_chunk import TranscriptChunk
from security.webhooks import verify_karpathys_secret
from services.voice_ingest import (
    acknowledge,
    call_sid,
    exact_session,
    find_call,
    lock_call,
    replay,
    resolve_lead,
    start_session,
)

router = APIRouter(dependencies=[Depends(verify_karpathys_secret)])


@router.get('/connection')
async def connection(challenge: UUID):
    from services.connection_status import receiver_identity, source_tenant
    return {'schema_version': 1, 'service': 'karpathys-dashboard', 'challenge': str(challenge), 'source_tenant_id': source_tenant(), 'receiver_id': receiver_identity()}


@router.post("/call")
async def ingest_call(body: dict, session: AsyncSession = Depends(get_session)):
    sid = call_sid(body)
    await lock_call(session, sid)
    rows = (await session.scalars(select(Call).where(Call.provider == CallProvider.signalwire, Call.provider_call_id == sid).limit(2))).all()
    if len(rows) > 1 or (rows and rows[0].deleted_at is not None):
        raise HTTPException(409, "Provider call is ambiguous or deleted")
    if rows:
        call = rows[0]
    else:
        call = Call(provider=CallProvider.signalwire, provider_call_id=sid, call_status=CallStatus.connected, lead_id=await resolve_lead(session, body), started_at=datetime.now(UTC), metadata_={"external_source": "rei", "external_lead_id": body.get("lead_id")})
        session.add(call)
        await session.flush()
    existing, fingerprint = replay(call, "call", body)
    if existing:
        return existing
    conversation = await start_session(session, call) if not rows else await exact_session(session, call)
    return await acknowledge(session, call, "call", fingerprint, lead_id=str(call.lead_id) if call.lead_id else None, session_id=str(conversation.id))


@router.post("/turn")
async def ingest_turn(body: dict, session: AsyncSession = Depends(get_session)):
    sid = call_sid(body)
    speaker, text, index = body.get("speaker"), body.get("text"), body.get("turn_index")
    if speaker not in {"user", "seller", "sophia", "assistant", "system"} or not isinstance(text, str) or not text.strip() or len(text) > 16000 or type(index) is not int or not 0 <= index <= 10000:
        raise HTTPException(422, "Invalid conversation turn")
    await lock_call(session, sid)
    call = await find_call(session, sid)
    key = f"turn:{speaker}:{index}"
    existing, fingerprint = replay(call, key, body)
    if existing:
        return existing
    conversation = await exact_session(session, call)
    turn = SophiaTurn(session_id=conversation.id, turn_key=f"rei:{sid}:{speaker}:{index}", turn_index=index, status=SophiaTurnStatus.completed, input_payload={"speaker": speaker, "text": text}, completed_at=datetime.now(UTC))
    session.add(turn)
    conversation.turn_count = max(conversation.turn_count, index + 1)
    await session.flush()
    return await acknowledge(session, call, key, fingerprint, session_id=str(conversation.id), turn_id=str(turn.id))


async def finish(body, session, key, failed=False):
    sid = call_sid(body)
    duration = body.get("duration_seconds")
    if duration is not None and (type(duration) is not int or not 0 <= duration <= 86400):
        raise HTTPException(422, "Invalid call duration")
    await lock_call(session, sid)
    call = await find_call(session, sid)
    existing, fingerprint = replay(call, key, body)
    if existing:
        return existing
    if call.call_status != CallStatus.failed:
        call.call_status = CallStatus.failed if failed else CallStatus.completed
    call.ended_at = call.ended_at or datetime.now(UTC)
    if duration is not None:
        call.duration_seconds = duration
    metadata = dict(call.metadata_ or {})
    if body.get("raw_disposition") or body.get("disposition"):
        metadata["disposition_advisory"] = body.get("raw_disposition") or body.get("disposition")
    call.metadata_ = metadata
    conversation = await exact_session(session, call)
    conversation.status = SophiaSessionStatus.failed if call.call_status == CallStatus.failed else SophiaSessionStatus.completed
    conversation.completed_at = call.ended_at
    return await acknowledge(session, call, key, fingerprint, session_id=str(conversation.id))


@router.post("/complete")
async def ingest_complete(body: dict, session: AsyncSession = Depends(get_session)):
    return await finish(body, session, "complete")


@router.post("/ended")
async def ingest_ended(body: dict, session: AsyncSession = Depends(get_session)):
    return await finish(body, session, "ended")


@router.post("/failed")
async def ingest_failed(body: dict, session: AsyncSession = Depends(get_session)):
    return await finish(body, session, "failed", True)


@router.post("/transcript")
async def ingest_transcript(body: dict, session: AsyncSession = Depends(get_session)):
    sid = call_sid(body)
    chunks = body.get("chunks")
    if not isinstance(chunks, list) or not 1 <= len(chunks) <= 2000 or body.get("chunk_count") != len(chunks):
        raise HTTPException(422, "Transcript chunks and matching chunk_count are required")
    for chunk in chunks:
        if not isinstance(chunk, dict) or not isinstance(chunk.get("speaker"), str) or not isinstance(chunk.get("text"), str) or not chunk["text"].strip() or len(chunk["text"]) > 16000 or len(chunk["speaker"]) > 32:
            raise HTTPException(422, "Invalid transcript chunk")
    if sum(len(chunk["text"]) for chunk in chunks) > 250000:
        raise HTTPException(413, "Transcript text budget exceeded")
    await lock_call(session, sid)
    call = await find_call(session, sid)
    if body.get("lead_id") is not None and body["lead_id"] != (call.metadata_ or {}).get("external_lead_id"):
        raise HTTPException(409, "Transcript lead does not match its provider call")
    existing, fingerprint = replay(call, "transcript", body)
    if existing:
        return existing
    transcript = Transcript(source_type=TranscriptSourceType.call, call_id=call.id, lead_id=call.lead_id, transcript_status=TranscriptStatus.completed)
    session.add(transcript)
    await session.flush()
    session.add_all([TranscriptChunk(transcript_id=transcript.id, chunk_index=i, speaker=chunk["speaker"], text=chunk["text"]) for i, chunk in enumerate(chunks)])
    return await acknowledge(session, call, "transcript", fingerprint, transcript_id=str(transcript.id), chunk_count=len(chunks))


@router.post("/business")
async def ingest_business(body: dict, session: AsyncSession = Depends(get_session)):
    from services.business_evidence import receive_business
    return await receive_business(session, body)
