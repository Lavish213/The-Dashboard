"""
TranscriptSearchIndex — metadata indexing foundation.

Writes a denormalized JSONB snapshot to Transcript.metadata_ for future
search use. No vector embeddings. No semantic search. Pure metadata.

build_index()     — compute and persist index for one transcript.
search_by_source()— basic metadata filter on source_type.
search_by_speaker()— filter transcripts that contain a given speaker.

The index schema stored in metadata_:
{
  "speakers": ["agent", "lead"],
  "chunk_count": 42,
  "source_type": "call",
  "stream_count": 2,
  "has_failures": false,
  "indexed_at": "2026-01-01T00:00:00Z"
}

This schema is intentionally simple — future phases may add tsv search
columns, GIN indices, or fulltext support.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.transcript import Transcript
from models.transcript_chunk import TranscriptChunk
from models.transcript_stream import TranscriptStream
from transcripts.repositories.transcript import TranscriptRepository


class TranscriptSearchIndex:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TranscriptRepository(session)

    async def build_index(self, transcript_id: UUID) -> dict:
        """
        Compute metadata index and persist to Transcript.metadata_.
        Returns the written index dict.
        """
        transcript = await self._repo.get_for_update_or_raise(transcript_id)

        # Unique speakers from chunks
        speaker_result = await self._session.execute(
            select(TranscriptChunk.speaker)
            .where(TranscriptChunk.transcript_id == transcript_id)
            .distinct()
        )
        speakers = [row[0] for row in speaker_result.all()]

        # Chunk count
        chunk_count_result = await self._session.execute(
            select(func.count()).select_from(TranscriptChunk)
            .where(TranscriptChunk.transcript_id == transcript_id)
        )
        chunk_count = chunk_count_result.scalar_one()

        # Stream count + failure flag
        stream_result = await self._session.execute(
            select(TranscriptStream.status)
            .where(TranscriptStream.transcript_id == transcript_id)
        )
        stream_statuses = [row[0] for row in stream_result.all()]
        has_failures = any(
            str(s) in ("failed", "cancelled") for s in stream_statuses
        )

        index = {
            "speakers": speakers,
            "chunk_count": chunk_count,
            "source_type": str(transcript.source_type),
            "stream_count": len(stream_statuses),
            "has_failures": has_failures,
            "indexed_at": datetime.now(UTC).isoformat(),
        }

        transcript.metadata_ = index
        self._session.add(transcript)
        await self._session.flush()

        return index

    async def search_by_source(
        self, source_type: str
    ) -> list[UUID]:
        """Return transcript IDs matching source_type metadata."""

        result = await self._session.execute(
            select(Transcript.id).where(
                Transcript.metadata_["source_type"].as_string() == source_type,
                Transcript.deleted_at.is_(None),
            )
        )
        return [row[0] for row in result.all()]

    async def search_by_speaker(
        self, speaker: str
    ) -> list[UUID]:
        """Return transcript IDs where metadata speakers list contains speaker."""
        result = await self._session.execute(
            select(Transcript.id).where(
                Transcript.metadata_["speakers"].contains(f'"{speaker}"'),
                Transcript.deleted_at.is_(None),
            )
        )
        return [row[0] for row in result.all()]
