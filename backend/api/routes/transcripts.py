"""Transcript API routes — pagination mandatory, deterministic ordering."""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from db.session import get_session
from transcripts.repositories.chunk import TranscriptChunkRepository
from transcripts.repositories.event import TranscriptEventRepository
from transcripts.repositories.transcript import TranscriptRepository
from transcripts.runtime.runtime import TranscriptRuntime, TranscriptTransitionError
from transcripts.schemas.transcript import (
    TranscriptChunkCreate,
    TranscriptChunkResponse,
    TranscriptCreate,
    TranscriptEventResponse,
    TranscriptResponse,
)

router = APIRouter()

# ---------------------------------------------------------------------------
# Create / Get
# ---------------------------------------------------------------------------

@router.post("", response_model=TranscriptResponse, status_code=status.HTTP_201_CREATED)
async def create_transcript(
    body: TranscriptCreate,
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    rt = TranscriptRuntime(session)
    transcript = await rt.create(
        source_type=body.source_type,
        workflow_id=body.workflow_id,
        call_id=body.call_id,
        lead_id=body.lead_id,
    )
    return TranscriptResponse.model_validate(transcript)


@router.get("/{transcript_id}", response_model=TranscriptResponse)
async def get_transcript(
    transcript_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    repo = TranscriptRepository(session)
    transcript = await repo.get_by_id_or_raise(transcript_id)
    return TranscriptResponse.model_validate(transcript)


# ---------------------------------------------------------------------------
# Lifecycle transitions
# ---------------------------------------------------------------------------

@router.post("/{transcript_id}/start", response_model=TranscriptResponse)
async def start_transcript(
    transcript_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    try:
        rt = TranscriptRuntime(session)
        transcript = await rt.start(transcript_id)
        return TranscriptResponse.model_validate(transcript)
    except TranscriptTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{transcript_id}/pause", response_model=TranscriptResponse)
async def pause_transcript(
    transcript_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    try:
        rt = TranscriptRuntime(session)
        transcript = await rt.pause(transcript_id)
        return TranscriptResponse.model_validate(transcript)
    except TranscriptTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{transcript_id}/resume", response_model=TranscriptResponse)
async def resume_transcript(
    transcript_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    try:
        rt = TranscriptRuntime(session)
        transcript = await rt.resume(transcript_id)
        return TranscriptResponse.model_validate(transcript)
    except TranscriptTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{transcript_id}/complete", response_model=TranscriptResponse)
async def complete_transcript(
    transcript_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    try:
        rt = TranscriptRuntime(session)
        transcript = await rt.complete(transcript_id)
        return TranscriptResponse.model_validate(transcript)
    except TranscriptTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{transcript_id}/fail", response_model=TranscriptResponse)
async def fail_transcript(
    transcript_id: UUID,
    reason: str = Query(default=""),
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    try:
        rt = TranscriptRuntime(session)
        transcript = await rt.fail(transcript_id, reason=reason)
        return TranscriptResponse.model_validate(transcript)
    except TranscriptTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.post("/{transcript_id}/archive", response_model=TranscriptResponse)
async def archive_transcript(
    transcript_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> TranscriptResponse:
    try:
        rt = TranscriptRuntime(session)
        transcript = await rt.archive(transcript_id)
        return TranscriptResponse.model_validate(transcript)
    except TranscriptTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


# ---------------------------------------------------------------------------
# Chunks — append + paginated retrieval
# ---------------------------------------------------------------------------

@router.post("/{transcript_id}/chunks", response_model=TranscriptChunkResponse, status_code=status.HTTP_201_CREATED)
async def append_chunk(
    transcript_id: UUID,
    body: TranscriptChunkCreate,
    session: AsyncSession = Depends(get_session),
) -> TranscriptChunkResponse:
    try:
        rt = TranscriptRuntime(session)
        chunk = await rt.append_chunk(
            transcript_id=transcript_id,
            speaker=body.speaker,
            text=body.text,
            stream_type=body.stream_type,
            chunk_index=body.chunk_index,
        )
        return TranscriptChunkResponse.model_validate(chunk)
    except TranscriptTransitionError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))


@router.get("/{transcript_id}/chunks", response_model=list[TranscriptChunkResponse])
async def get_chunks(
    transcript_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> list[TranscriptChunkResponse]:
    repo = TranscriptRepository(session)
    await repo.get_by_id_or_raise(transcript_id)  # 404 guard
    chunk_repo = TranscriptChunkRepository(session)
    result = await chunk_repo.get_by_transcript(transcript_id, page=page, page_size=page_size)
    return [TranscriptChunkResponse.model_validate(c) for c in result.items]


# ---------------------------------------------------------------------------
# Events — paginated replay
# ---------------------------------------------------------------------------

@router.get("/{transcript_id}/events", response_model=list[TranscriptEventResponse])
async def get_events(
    transcript_id: UUID,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[TranscriptEventResponse]:
    repo = TranscriptRepository(session)
    await repo.get_by_id_or_raise(transcript_id)  # 404 guard
    event_repo = TranscriptEventRepository(session)
    result = await event_repo.get_by_transcript(transcript_id, page=page, page_size=page_size)
    return [TranscriptEventResponse.model_validate(e) for e in result.items]


@router.get("/{transcript_id}/replay")
async def replay_transcript(
    transcript_id: UUID,
    session: AsyncSession = Depends(get_session),
) -> dict:
    rt = TranscriptRuntime(session)
    result = await rt.replay(transcript_id)
    return {
        "transcript_id": str(result.transcript_id),
        "replayed_events": result.replayed_events,
        "final_status": result.final_status,
        "chunk_count": result.chunk_count,
    }
