"""
StreamReconstructor — deterministic full-text reconstruction from chunks.

Reads TranscriptChunk rows ordered by chunk_index and concatenates them.
Read-only. No mutations. Deterministic: same chunks → same text.

reconstruct()       — full transcript text from all chunks.
reconstruct_from()  — text from after a checkpoint position.
reconstruct_stream()— text contributed by a specific stream session.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.transcript_chunk import TranscriptChunk
from transcripts.contracts import ReconstructionResult
from transcripts.repositories.chunk import TranscriptChunkRepository
from transcripts.repositories.stream import TranscriptStreamRepository


class StreamReconstructor:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._chunks = TranscriptChunkRepository(session)
        self._streams = TranscriptStreamRepository(session)

    async def reconstruct(
        self, transcript_id: UUID
    ) -> ReconstructionResult:
        """
        Full reconstruction from all chunks, ordered by chunk_index.
        Separator: single space between speaker turns.
        """
        result = await self._session.execute(
            select(TranscriptChunk)
            .where(TranscriptChunk.transcript_id == transcript_id)
            .order_by(TranscriptChunk.chunk_index.asc(), TranscriptChunk.id.asc())
        )
        chunks = list(result.scalars().all())
        return _build_result(transcript_id, chunks, from_index=0)

    async def reconstruct_from(
        self,
        transcript_id: UUID,
        after_chunk_index: int,
        limit: int = 0,
    ) -> ReconstructionResult:
        """
        Reconstruction from chunks after after_chunk_index (exclusive).
        limit=0 means no limit.
        """
        q = (
            select(TranscriptChunk)
            .where(
                TranscriptChunk.transcript_id == transcript_id,
                TranscriptChunk.chunk_index > after_chunk_index,
            )
            .order_by(TranscriptChunk.chunk_index.asc(), TranscriptChunk.id.asc())
        )
        if limit > 0:
            q = q.limit(limit)
        result = await self._session.execute(q)
        chunks = list(result.scalars().all())
        return _build_result(transcript_id, chunks, from_index=after_chunk_index + 1)

    async def reconstruct_stream(
        self,
        transcript_id: UUID,
        stream_id: UUID,
    ) -> ReconstructionResult:
        """
        Reconstruction limited to chunks committed by a specific stream.
        Requires that stream has last_chunk_index set.
        Falls back to full reconstruction if stream has no committed chunks.
        """
        stream = await self._streams.get_by_id(stream_id)
        if stream is None or stream.last_chunk_index is None:
            return ReconstructionResult(
                transcript_id=transcript_id,
                full_text="",
                chunk_count=0,
                speakers=[],
                from_chunk_index=0,
                to_chunk_index=None,
            )

        # Approximation: reconstruct all chunks up to last_chunk_index.
        # A future multi-stream schema could tag chunks with stream_id.
        result = await self._session.execute(
            select(TranscriptChunk)
            .where(
                TranscriptChunk.transcript_id == transcript_id,
                TranscriptChunk.chunk_index <= stream.last_chunk_index,
            )
            .order_by(TranscriptChunk.chunk_index.asc(), TranscriptChunk.id.asc())
        )
        chunks = list(result.scalars().all())
        return _build_result(transcript_id, chunks, from_index=0)


def _build_result(
    transcript_id: UUID,
    chunks: list[TranscriptChunk],
    from_index: int,
) -> ReconstructionResult:
    texts = [c.text for c in chunks]
    speakers = list(dict.fromkeys(c.speaker for c in chunks))
    to_index = chunks[-1].chunk_index if chunks else None
    return ReconstructionResult(
        transcript_id=transcript_id,
        full_text=" ".join(texts),
        chunk_count=len(chunks),
        speakers=speakers,
        from_chunk_index=from_index,
        to_chunk_index=to_index,
    )
