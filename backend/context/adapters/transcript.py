"""
TranscriptContextAdapter — bridge TranscriptChunk rows into ContextItems.

Loads committed chunks for a transcript and converts them to ContextItems
for use in context assembly. Each chunk becomes one ContextItem.

Token count is estimated from text length when not pre-computed.
Priority defaults to 1 (below system layer at 0).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from context.contracts import ContextItem
from models.enums import ContextLayerType
from models.transcript_chunk import TranscriptChunk

_DEFAULT_PRIORITY = 1
_CHARS_PER_TOKEN = 4  # rough estimate for token counting


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


class TranscriptContextAdapter:
    """
    Load transcript chunks and convert to ContextItems.

    load(transcript_id, from_chunk_index, to_chunk_index) → list[ContextItem]
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(
        self,
        transcript_id: UUID,
        from_chunk_index: int = 0,
        to_chunk_index: int | None = None,
        priority: int = _DEFAULT_PRIORITY,
    ) -> list[ContextItem]:
        """
        Load TranscriptChunks for transcript_id and convert to ContextItems.

        Range: [from_chunk_index, to_chunk_index] inclusive.
        If to_chunk_index is None, load all chunks from from_chunk_index.
        """
        q = (
            select(TranscriptChunk)
            .where(
                TranscriptChunk.transcript_id == transcript_id,
                TranscriptChunk.chunk_index >= from_chunk_index,
            )
            .order_by(TranscriptChunk.chunk_index.asc())
        )
        if to_chunk_index is not None:
            q = q.where(TranscriptChunk.chunk_index <= to_chunk_index)

        result = await self._session.execute(q)
        chunks = result.scalars().all()

        return [
            ContextItem(
                layer=ContextLayerType.transcript,
                source_id=transcript_id,
                source_type="transcript_chunk",
                content=f"[{chunk.speaker}] {chunk.text}",
                token_count=_estimate_tokens(chunk.text),
                priority=priority,
                created_at=chunk.created_at,
                metadata={"chunk_index": chunk.chunk_index, "speaker": chunk.speaker},
            )
            for chunk in chunks
        ]
