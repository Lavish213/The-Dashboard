from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.transcript import Transcript
from models.transcript_segment import TranscriptSegment
from repositories.base import BaseRepository


class TranscriptRepository(BaseRepository[Transcript]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Transcript)

    async def get_by_lead(self, lead_id: UUID) -> list[Transcript]:
        result = await self.session.execute(
            select(Transcript).where(
                Transcript.lead_id == lead_id,
                Transcript.deleted_at.is_(None),
            ).order_by(Transcript.created_at.desc())
        )
        return list(result.scalars().all())

class TranscriptSegmentRepository(BaseRepository[TranscriptSegment]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, TranscriptSegment)

    async def get_by_transcript(self, transcript_id: UUID) -> list[TranscriptSegment]:
        result = await self.session.execute(
            select(TranscriptSegment).where(
                TranscriptSegment.transcript_id == transcript_id,
            ).order_by(TranscriptSegment.start_ms.asc())
        )
        return list(result.scalars().all())
