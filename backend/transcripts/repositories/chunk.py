"""TranscriptChunk repository — append-only, deterministic ordering."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.transcript_chunk import TranscriptChunk
from repositories.base import BaseRepository, PageResult


class TranscriptChunkRepository(BaseRepository[TranscriptChunk]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, TranscriptChunk)

    async def next_chunk_index(self, transcript_id: UUID) -> int:
        """Return the next chunk_index for a transcript (MAX + 1)."""
        result = await self.session.execute(
            select(func.coalesce(func.max(TranscriptChunk.chunk_index) + 1, 0))
            .where(TranscriptChunk.transcript_id == transcript_id)
        )
        return result.scalar_one()

    async def append(
        self,
        transcript_id: UUID,
        speaker: str,
        text: str,
        stream_type,
        chunk_index: int | None = None,
    ) -> TranscriptChunk:
        """
        Append a chunk. If chunk_index is None, auto-increments.
        Caller must hold row lock on Transcript row for safe concurrent append.
        """
        idx = chunk_index if chunk_index is not None else await self.next_chunk_index(transcript_id)
        return await self.create(
            transcript_id=transcript_id,
            chunk_index=idx,
            speaker=speaker,
            text=text,
            stream_type=stream_type,
        )

    async def get_by_transcript(
        self,
        transcript_id: UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> PageResult[TranscriptChunk]:
        """Paginated ordered chunk retrieval. Ordering: chunk_index, id."""
        from sqlalchemy import func as sqlfunc

        count_q = (
            select(sqlfunc.count())
            .select_from(TranscriptChunk)
            .where(TranscriptChunk.transcript_id == transcript_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()

        q = (
            select(TranscriptChunk)
            .where(TranscriptChunk.transcript_id == transcript_id)
            .order_by(TranscriptChunk.chunk_index.asc(), TranscriptChunk.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.execute(q)).scalars().all())
        return PageResult(items=items, total=total, page=page, page_size=page_size)

    async def get_after_index(
        self,
        transcript_id: UUID,
        after_chunk_index: int,
        limit: int = 50,
    ) -> list[TranscriptChunk]:
        """Fetch chunks after a given index — for websocket incremental streaming."""
        result = await self.session.execute(
            select(TranscriptChunk)
            .where(
                TranscriptChunk.transcript_id == transcript_id,
                TranscriptChunk.chunk_index > after_chunk_index,
            )
            .order_by(TranscriptChunk.chunk_index.asc(), TranscriptChunk.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
