"""
Transcript runtime engine.

Responsibilities: create, append_chunk, pause, resume, complete, fail, archive, replay.
Append-only events. Atomic writes. SELECT FOR UPDATE for concurrent safety.
No intelligence layer. No summarization. No extraction.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import TranscriptSourceType, TranscriptStatus, TranscriptStreamType
from models.transcript import Transcript
from models.transcript_chunk import TranscriptChunk
from models.transcript_event import TranscriptEvent
from transcripts.repositories.chunk import TranscriptChunkRepository
from transcripts.repositories.event import TranscriptEventRepository
from transcripts.repositories.transcript import TranscriptRepository
from transcripts.runtime.states import TranscriptTransitionError, validate_transition

# Event type constants
EVT_TRANSCRIPT_CREATED = "transcript.created"
EVT_TRANSCRIPT_STARTED = "transcript.started"
EVT_TRANSCRIPT_CHUNK_ADDED = "transcript.chunk_added"
EVT_TRANSCRIPT_PAUSED = "transcript.paused"
EVT_TRANSCRIPT_RESUMED = "transcript.resumed"
EVT_TRANSCRIPT_COMPLETED = "transcript.completed"
EVT_TRANSCRIPT_FAILED = "transcript.failed"
EVT_TRANSCRIPT_ARCHIVED = "transcript.archived"

# Status-event mapping for replay
_STATUS_EVENTS: dict[str, TranscriptStatus] = {
    EVT_TRANSCRIPT_CREATED: TranscriptStatus.created,
    EVT_TRANSCRIPT_STARTED: TranscriptStatus.active,
    EVT_TRANSCRIPT_PAUSED: TranscriptStatus.paused,
    EVT_TRANSCRIPT_RESUMED: TranscriptStatus.active,
    EVT_TRANSCRIPT_COMPLETED: TranscriptStatus.completed,
    EVT_TRANSCRIPT_FAILED: TranscriptStatus.failed,
    EVT_TRANSCRIPT_ARCHIVED: TranscriptStatus.archived,
}


@dataclass(frozen=True)
class ReplayResult:
    transcript_id: UUID
    replayed_events: int
    final_status: TranscriptStatus
    chunk_count: int


class TranscriptRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TranscriptRepository(session)
        self._chunks = TranscriptChunkRepository(session)
        self._events = TranscriptEventRepository(session)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def create(
        self,
        source_type: TranscriptSourceType = TranscriptSourceType.call,
        workflow_id: UUID | None = None,
        call_id: UUID | None = None,
        lead_id: UUID | None = None,
    ) -> Transcript:
        """Create transcript in created state and emit created event."""
        transcript = await self._repo.create(
            transcript_status=TranscriptStatus.created,
            source_type=source_type,
            workflow_id=workflow_id,
            call_id=call_id,
            lead_id=lead_id,
        )
        await self._emit(transcript, EVT_TRANSCRIPT_CREATED, {
            "source_type": source_type,
            "workflow_id": str(workflow_id) if workflow_id else None,
        })
        return transcript

    async def start(self, transcript_id: UUID) -> Transcript:
        """Transition created → active."""
        return await self._transition(
            transcript_id,
            target=TranscriptStatus.active,
            event_type=EVT_TRANSCRIPT_STARTED,
            payload={},
        )

    async def pause(self, transcript_id: UUID, reason: str = "") -> Transcript:
        return await self._transition(
            transcript_id,
            target=TranscriptStatus.paused,
            event_type=EVT_TRANSCRIPT_PAUSED,
            payload={"reason": reason},
        )

    async def resume(self, transcript_id: UUID) -> Transcript:
        return await self._transition(
            transcript_id,
            target=TranscriptStatus.active,
            event_type=EVT_TRANSCRIPT_RESUMED,
            payload={},
        )

    async def complete(self, transcript_id: UUID, duration_seconds: int | None = None) -> Transcript:
        transcript = await self._repo.get_for_update_or_raise(transcript_id)
        validate_transition(transcript_id, transcript.transcript_status, TranscriptStatus.completed)

        transcript.transcript_status = TranscriptStatus.completed
        if duration_seconds is not None:
            transcript.duration_seconds = duration_seconds
        self._session.add(transcript)
        await self._session.flush()

        await self._emit(transcript, EVT_TRANSCRIPT_COMPLETED, {
            "duration_seconds": duration_seconds,
        })
        return transcript

    async def fail(self, transcript_id: UUID, reason: str) -> Transcript:
        return await self._transition(
            transcript_id,
            target=TranscriptStatus.failed,
            event_type=EVT_TRANSCRIPT_FAILED,
            payload={"reason": reason},
        )

    async def archive(self, transcript_id: UUID) -> Transcript:
        return await self._transition(
            transcript_id,
            target=TranscriptStatus.archived,
            event_type=EVT_TRANSCRIPT_ARCHIVED,
            payload={},
        )

    # ------------------------------------------------------------------
    # Chunk append
    # ------------------------------------------------------------------

    async def append_chunk(
        self,
        transcript_id: UUID,
        speaker: str,
        text: str,
        stream_type: TranscriptStreamType = TranscriptStreamType.user,
        chunk_index: int | None = None,
    ) -> TranscriptChunk:
        """
        Append a chunk atomically.
        Acquires row lock on Transcript before computing next chunk_index.
        Transcript must be active.
        """
        transcript = await self._repo.get_for_update_or_raise(transcript_id)

        if transcript.transcript_status != TranscriptStatus.active:
            raise TranscriptTransitionError(
                transcript_id,
                transcript.transcript_status,
                TranscriptStatus.active,
                reason="transcript must be active to append chunks",
            )

        chunk = await self._chunks.append(
            transcript_id=transcript_id,
            speaker=speaker,
            text=text,
            stream_type=stream_type,
            chunk_index=chunk_index,
        )

        await self._emit(transcript, EVT_TRANSCRIPT_CHUNK_ADDED, {
            "chunk_index": chunk.chunk_index,
            "speaker": speaker,
            "stream_type": stream_type,
        })

        return chunk

    # ------------------------------------------------------------------
    # Replay — read-only
    # ------------------------------------------------------------------

    async def replay(self, transcript_id: UUID) -> ReplayResult:
        """
        Derive transcript state from event log.
        Read-only. Does NOT mutate DB.
        Deterministic: same events → same result.
        """
        await self._repo.get_by_id_or_raise(transcript_id)  # 404 guard
        events = await self._events.get_all_ordered(transcript_id)

        derived_status = TranscriptStatus.created
        for event in events:
            if event.event_type in _STATUS_EVENTS:
                derived_status = _STATUS_EVENTS[event.event_type]

        chunk_count = sum(1 for e in events if e.event_type == EVT_TRANSCRIPT_CHUNK_ADDED)

        return ReplayResult(
            transcript_id=transcript_id,
            replayed_events=len(events),
            final_status=derived_status,
            chunk_count=chunk_count,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _transition(
        self,
        transcript_id: UUID,
        target: TranscriptStatus,
        event_type: str,
        payload: dict,
    ) -> Transcript:
        transcript = await self._repo.get_for_update_or_raise(transcript_id)
        validate_transition(transcript_id, transcript.transcript_status, target)

        transcript.transcript_status = target
        self._session.add(transcript)
        await self._session.flush()

        await self._emit(transcript, event_type, payload)
        return transcript

    async def _emit(
        self,
        transcript: Transcript,
        event_type: str,
        payload: dict,
    ) -> TranscriptEvent:
        return await self._events.append_event(
            transcript_id=transcript.id,
            event_type=event_type,
            payload=payload,
        )
