"""
TranscriptStreamRuntime — streaming session lifecycle manager.

State machine:
  pending → active → completed
                   → interrupted  (resumable: → active)
                   → cancelled    (terminal)
                   → failed       (terminal)

commit_chunk()   — flush partial_text to TranscriptChunk, update cursor.
receive_partial()— update in-flight partial_text buffer (mutable).
resume()         — interrupted → active; restores stream from last_chunk_index.

All lifecycle mutations:
  - persist to transcript_streams row (SELECT FOR UPDATE)
  - append event to transcript_events

Idempotency:
  create()  — returns existing stream if stream_key already registered.
  cancel()  — no-op if already terminal.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import TranscriptStreamStatus, TranscriptStreamType
from models.transcript_stream import TranscriptStream
from transcripts.contracts import StreamChunkResult, StreamResult
from transcripts.repositories.chunk import TranscriptChunkRepository
from transcripts.repositories.event import TranscriptEventRepository
from transcripts.repositories.stream import TranscriptStreamRepository

logger = structlog.get_logger(__name__)

EVT_STREAM_CREATED = "stream.created"
EVT_STREAM_STARTED = "stream.started"
EVT_STREAM_CHUNK_COMMITTED = "stream.chunk_committed"
EVT_STREAM_PARTIAL_UPDATED = "stream.partial_updated"
EVT_STREAM_COMPLETED = "stream.completed"
EVT_STREAM_INTERRUPTED = "stream.interrupted"
EVT_STREAM_RESUMED = "stream.resumed"
EVT_STREAM_CANCELLED = "stream.cancelled"
EVT_STREAM_FAILED = "stream.failed"

_TERMINAL = frozenset({
    TranscriptStreamStatus.cancelled,
    TranscriptStreamStatus.failed,
    TranscriptStreamStatus.completed,
})


class StreamStateError(Exception):
    """Raised on illegal stream state transitions."""


class TranscriptStreamRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TranscriptStreamRepository(session)
        self._chunks = TranscriptChunkRepository(session)
        self._events = TranscriptEventRepository(session)

    # ------------------------------------------------------------------
    # create
    # ------------------------------------------------------------------

    async def create(
        self,
        transcript_id: UUID,
        stream_key: str,
        provider: str | None = None,
        model_name: str | None = None,
    ) -> StreamResult:
        """
        Create a new stream session. Idempotent: same stream_key → same stream.
        """
        existing = await self._repo.get_by_key(stream_key)
        if existing is not None:
            return _to_result(existing)

        row = TranscriptStream(
            transcript_id=transcript_id,
            stream_key=stream_key,
            status=TranscriptStreamStatus.pending,
            provider=provider,
            model_name=model_name,
        )
        self._session.add(row)
        await self._session.flush()

        await self._emit(transcript_id, row.id, EVT_STREAM_CREATED, {
            "stream_key": stream_key,
            "provider": provider,
            "model_name": model_name,
        })

        logger.info("stream.created", stream_id=str(row.id), key=stream_key)
        return _to_result(row)

    # ------------------------------------------------------------------
    # start
    # ------------------------------------------------------------------

    async def start(self, stream_id: UUID) -> StreamResult:
        """pending → active."""
        row = await self._repo.get_for_update_or_raise(stream_id)
        if row.status != TranscriptStreamStatus.pending:
            raise StreamStateError(f"cannot start stream in state {row.status}")

        row.status = TranscriptStreamStatus.active
        row.started_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        await self._emit(row.transcript_id, stream_id, EVT_STREAM_STARTED, {})
        logger.info("stream.started", stream_id=str(stream_id))
        return _to_result(row)

    # ------------------------------------------------------------------
    # receive_partial — mutable buffer update
    # ------------------------------------------------------------------

    async def receive_partial(
        self,
        stream_id: UUID,
        text: str,
    ) -> None:
        """
        Update in-flight partial_text. Must be active.
        Not append-only — overwrites existing partial.
        Emits stream.partial_updated event.
        """
        row = await self._repo.get_for_update_or_raise(stream_id)
        if row.status != TranscriptStreamStatus.active:
            raise StreamStateError(
                f"cannot update partial in state {row.status}"
            )

        row.partial_text = text
        self._session.add(row)
        await self._session.flush()

        await self._emit(row.transcript_id, stream_id, EVT_STREAM_PARTIAL_UPDATED, {
            "length": len(text),
        })

    # ------------------------------------------------------------------
    # commit_chunk — flush partial to chunk
    # ------------------------------------------------------------------

    async def commit_chunk(
        self,
        stream_id: UUID,
        speaker: str,
        text: str,
        stream_type: TranscriptStreamType = TranscriptStreamType.agent,
        tokens_output: int = 0,
    ) -> StreamChunkResult:
        """
        Persist text as TranscriptChunk and clear partial_text.
        Updates last_chunk_index and tokens_output.
        Must be active.
        """
        row = await self._repo.get_for_update_or_raise(stream_id)
        if row.status != TranscriptStreamStatus.active:
            raise StreamStateError(
                f"cannot commit chunk in state {row.status}"
            )

        chunk = await self._chunks.append(
            transcript_id=row.transcript_id,
            speaker=speaker,
            text=text,
            stream_type=stream_type,
        )

        row.last_chunk_index = chunk.chunk_index
        row.partial_text = None
        row.tokens_output = (row.tokens_output or 0) + tokens_output
        self._session.add(row)
        await self._session.flush()

        await self._emit(row.transcript_id, stream_id, EVT_STREAM_CHUNK_COMMITTED, {
            "chunk_index": chunk.chunk_index,
            "speaker": speaker,
            "stream_type": str(stream_type),
            "tokens_output": tokens_output,
        })

        return StreamChunkResult(
            stream_id=stream_id,
            chunk_id=chunk.id,
            chunk_index=chunk.chunk_index,
            tokens_output_cumulative=row.tokens_output,
        )

    # ------------------------------------------------------------------
    # complete
    # ------------------------------------------------------------------

    async def complete(
        self,
        stream_id: UUID,
        tokens_input: int = 0,
        tokens_output: int = 0,
    ) -> StreamResult:
        """
        active → completed. Finalizes token counts. Clears partial_text.
        """
        row = await self._repo.get_for_update_or_raise(stream_id)
        if row.status != TranscriptStreamStatus.active:
            raise StreamStateError(
                f"cannot complete stream in state {row.status}"
            )

        row.status = TranscriptStreamStatus.completed
        row.completed_at = datetime.now(UTC)
        row.partial_text = None
        row.tokens_input = tokens_input
        row.tokens_output = (row.tokens_output or 0) + tokens_output
        self._session.add(row)
        await self._session.flush()

        await self._emit(row.transcript_id, stream_id, EVT_STREAM_COMPLETED, {
            "tokens_input": row.tokens_input,
            "tokens_output": row.tokens_output,
        })

        logger.info("stream.completed", stream_id=str(stream_id))
        return _to_result(row)

    # ------------------------------------------------------------------
    # interrupt — resumable
    # ------------------------------------------------------------------

    async def interrupt(
        self,
        stream_id: UUID,
        reason: str = "",
    ) -> StreamResult:
        """
        active → interrupted. Preserves last_chunk_index for resume.
        Discards partial_text (incomplete fragment).
        """
        row = await self._repo.get_for_update_or_raise(stream_id)
        if row.status != TranscriptStreamStatus.active:
            raise StreamStateError(
                f"cannot interrupt stream in state {row.status}"
            )

        row.status = TranscriptStreamStatus.interrupted
        row.interrupted_at = datetime.now(UTC)
        row.interruption_reason = reason or None
        row.partial_text = None
        self._session.add(row)
        await self._session.flush()

        await self._emit(row.transcript_id, stream_id, EVT_STREAM_INTERRUPTED, {
            "reason": reason,
            "last_chunk_index": row.last_chunk_index,
        })

        logger.info("stream.interrupted", stream_id=str(stream_id), reason=reason)
        return _to_result(row)

    # ------------------------------------------------------------------
    # resume — interrupted → active
    # ------------------------------------------------------------------

    async def resume(self, stream_id: UUID) -> StreamResult:
        """
        interrupted → active. Caller should restore from last_chunk_index.
        """
        row = await self._repo.get_for_update_or_raise(stream_id)
        if row.status != TranscriptStreamStatus.interrupted:
            raise StreamStateError(
                f"cannot resume stream in state {row.status}"
            )

        row.status = TranscriptStreamStatus.active
        row.started_at = datetime.now(UTC)
        self._session.add(row)
        await self._session.flush()

        await self._emit(row.transcript_id, stream_id, EVT_STREAM_RESUMED, {
            "resume_from_chunk_index": row.last_chunk_index,
        })

        logger.info("stream.resumed", stream_id=str(stream_id))
        return _to_result(row)

    # ------------------------------------------------------------------
    # cancel
    # ------------------------------------------------------------------

    async def cancel(
        self,
        stream_id: UUID,
        reason: str = "",
    ) -> StreamResult:
        """
        Cancel from any non-terminal state. Idempotent — no-op if terminal.
        """
        row = await self._repo.get_for_update_or_raise(stream_id)
        if row.status in _TERMINAL:
            return _to_result(row)

        row.status = TranscriptStreamStatus.cancelled
        row.cancel_reason = reason or None
        row.partial_text = None
        self._session.add(row)
        await self._session.flush()

        await self._emit(row.transcript_id, stream_id, EVT_STREAM_CANCELLED, {
            "reason": reason,
        })

        logger.info("stream.cancelled", stream_id=str(stream_id), reason=reason)
        return _to_result(row)

    # ------------------------------------------------------------------
    # fail
    # ------------------------------------------------------------------

    async def fail(
        self,
        stream_id: UUID,
        error: str,
    ) -> StreamResult:
        """Fail from any non-terminal state."""
        row = await self._repo.get_for_update_or_raise(stream_id)
        if row.status in _TERMINAL:
            return _to_result(row)

        row.status = TranscriptStreamStatus.failed
        row.error = error
        row.partial_text = None
        self._session.add(row)
        await self._session.flush()

        await self._emit(row.transcript_id, stream_id, EVT_STREAM_FAILED, {
            "error": error,
        })

        logger.info("stream.failed", stream_id=str(stream_id), error=error)
        return _to_result(row)

    # ------------------------------------------------------------------
    # internal
    # ------------------------------------------------------------------

    async def _emit(
        self,
        transcript_id: UUID,
        stream_id: UUID,
        event_type: str,
        payload: dict,
    ) -> None:
        await self._events.append_event(
            transcript_id=transcript_id,
            event_type=event_type,
            payload={"stream_id": str(stream_id), **payload},
        )


def _to_result(row: TranscriptStream) -> StreamResult:
    return StreamResult(
        stream_id=row.id,
        transcript_id=row.transcript_id,
        stream_key=row.stream_key,
        status=row.status,
        last_chunk_index=row.last_chunk_index,
        tokens_input=row.tokens_input or 0,
        tokens_output=row.tokens_output or 0,
    )
