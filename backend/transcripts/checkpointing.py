"""
TranscriptCheckpointRuntime — append-only resume markers.

set()           — idempotent checkpoint at chunk_index.
get_latest()    — most recent checkpoint for a transcript.
get_for_stream()— all checkpoints for a specific stream.
resume_from()   — fetch chunks after a checkpoint index.

Checkpoints are append-only. Existing (transcript_id, chunk_index) pairs
are never overwritten — attempting to re-checkpoint returns existing row.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from transcripts.contracts import CheckpointResult
from transcripts.repositories.checkpoint import TranscriptCheckpointRepository
from transcripts.repositories.chunk import TranscriptChunkRepository

logger = structlog.get_logger(__name__)


class TranscriptCheckpointRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TranscriptCheckpointRepository(session)
        self._chunks = TranscriptChunkRepository(session)

    async def set(
        self,
        transcript_id: UUID,
        chunk_index: int,
        state: dict | None = None,
        stream_id: UUID | None = None,
        label: str | None = None,
    ) -> CheckpointResult:
        """
        Create checkpoint at chunk_index. Idempotent on (transcript_id, chunk_index).
        """
        cp = await self._repo.set(
            transcript_id=transcript_id,
            chunk_index=chunk_index,
            state=state,
            stream_id=stream_id,
            label=label,
        )
        logger.info(
            "transcript.checkpoint.set",
            transcript_id=str(transcript_id),
            chunk_index=chunk_index,
        )
        return CheckpointResult(
            checkpoint_id=cp.id,
            transcript_id=transcript_id,
            stream_id=cp.stream_id,
            chunk_index=cp.chunk_index,
            label=cp.label,
            created_at=cp.created_at,
        )

    async def get_latest(
        self, transcript_id: UUID
    ) -> CheckpointResult | None:
        """Return the most recent checkpoint (highest chunk_index), or None."""
        cp = await self._repo.get_latest(transcript_id)
        if cp is None:
            return None
        return CheckpointResult(
            checkpoint_id=cp.id,
            transcript_id=transcript_id,
            stream_id=cp.stream_id,
            chunk_index=cp.chunk_index,
            label=cp.label,
            created_at=cp.created_at,
        )

    async def get_all(
        self, transcript_id: UUID
    ) -> list[CheckpointResult]:
        """Return all checkpoints ordered by chunk_index ascending."""
        cps = await self._repo.get_all(transcript_id)
        return [
            CheckpointResult(
                checkpoint_id=cp.id,
                transcript_id=transcript_id,
                stream_id=cp.stream_id,
                chunk_index=cp.chunk_index,
                label=cp.label,
                created_at=cp.created_at,
            )
            for cp in cps
        ]

    async def get_for_stream(
        self, stream_id: UUID
    ) -> list[CheckpointResult]:
        """Return all checkpoints for a specific stream."""
        cps = await self._repo.get_for_stream(stream_id)
        return [
            CheckpointResult(
                checkpoint_id=cp.id,
                transcript_id=cp.transcript_id,
                stream_id=cp.stream_id,
                chunk_index=cp.chunk_index,
                label=cp.label,
                created_at=cp.created_at,
            )
            for cp in cps
        ]

    async def chunks_since(
        self,
        transcript_id: UUID,
        after_chunk_index: int,
        limit: int = 100,
    ) -> list:
        """
        Fetch chunks after after_chunk_index (exclusive).
        Used for resume: caller provides the checkpoint's chunk_index.
        """
        return await self._chunks.get_after_index(
            transcript_id=transcript_id,
            after_chunk_index=after_chunk_index,
            limit=limit,
        )
