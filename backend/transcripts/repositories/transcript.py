"""Transcript repository — lifecycle persistence with row locking support."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import TranscriptSourceType, TranscriptStatus
from models.transcript import Transcript
from repositories.base import BaseRepository, PageResult


class TranscriptRepository(BaseRepository[Transcript]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Transcript)

    async def get_for_update(self, transcript_id: UUID) -> Transcript | None:
        """SELECT FOR UPDATE — holds row lock until transaction end."""
        result = await self.session.execute(
            select(Transcript).where(Transcript.id == transcript_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_for_update_or_raise(self, transcript_id: UUID) -> Transcript:
        from core.exceptions import NotFoundError
        transcript = await self.get_for_update(transcript_id)
        if transcript is None:
            raise NotFoundError(Transcript.__tablename__, str(transcript_id))
        return transcript

    async def get_by_workflow(
        self,
        workflow_id: UUID,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResult[Transcript]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[Transcript.workflow_id == workflow_id],
            order_by=Transcript.created_at.desc(),
        )

    async def get_by_status(
        self,
        status: TranscriptStatus,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResult[Transcript]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[Transcript.transcript_status == status],
            order_by=Transcript.created_at.desc(),
        )

    async def get_by_source_type(
        self,
        source_type: TranscriptSourceType,
        page: int = 1,
        page_size: int = 20,
    ) -> PageResult[Transcript]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[Transcript.source_type == source_type],
            order_by=Transcript.created_at.desc(),
        )
