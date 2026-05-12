"""TranscriptEvent repository — append-only, sequence-ordered replay."""
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.transcript_event import TranscriptEvent
from repositories.base import BaseRepository, PageResult


class TranscriptEventRepository(BaseRepository[TranscriptEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, TranscriptEvent)

    async def next_sequence(self, transcript_id: UUID) -> int:
        """Return next sequence number for a transcript (MAX + 1)."""
        result = await self.session.execute(
            select(func.coalesce(func.max(TranscriptEvent.sequence) + 1, 0))
            .where(TranscriptEvent.transcript_id == transcript_id)
        )
        return result.scalar_one()

    async def append_event(
        self,
        transcript_id: UUID,
        event_type: str,
        payload: dict,
    ) -> TranscriptEvent:
        """Append event with auto-incrementing sequence number."""
        seq = await self.next_sequence(transcript_id)
        return await self.create(
            transcript_id=transcript_id,
            event_type=event_type,
            sequence=seq,
            payload=payload,
        )

    async def get_by_transcript(
        self,
        transcript_id: UUID,
        page: int = 1,
        page_size: int = 100,
    ) -> PageResult[TranscriptEvent]:
        """Paginated sequence-ordered event retrieval."""
        from sqlalchemy import func as sqlfunc

        count_q = (
            select(sqlfunc.count())
            .select_from(TranscriptEvent)
            .where(TranscriptEvent.transcript_id == transcript_id)
        )
        total = (await self.session.execute(count_q)).scalar_one()

        q = (
            select(TranscriptEvent)
            .where(TranscriptEvent.transcript_id == transcript_id)
            .order_by(TranscriptEvent.sequence.asc(), TranscriptEvent.id.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = list((await self.session.execute(q)).scalars().all())
        return PageResult(items=items, total=total, page=page, page_size=page_size)

    async def get_all_ordered(self, transcript_id: UUID) -> list[TranscriptEvent]:
        """Full ordered event list — for replay only. Do NOT use for display."""
        result = await self.session.execute(
            select(TranscriptEvent)
            .where(TranscriptEvent.transcript_id == transcript_id)
            .order_by(TranscriptEvent.sequence.asc(), TranscriptEvent.id.asc())
        )
        return list(result.scalars().all())

    async def get_after_sequence(
        self,
        transcript_id: UUID,
        after_sequence: int,
        limit: int = 100,
    ) -> list[TranscriptEvent]:
        """Fetch events after a sequence checkpoint — for reconnect recovery."""
        result = await self.session.execute(
            select(TranscriptEvent)
            .where(
                TranscriptEvent.transcript_id == transcript_id,
                TranscriptEvent.sequence > after_sequence,
            )
            .order_by(TranscriptEvent.sequence.asc(), TranscriptEvent.id.asc())
            .limit(limit)
        )
        return list(result.scalars().all())
