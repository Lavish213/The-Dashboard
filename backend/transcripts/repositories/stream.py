"""TranscriptStream repository — stream session persistence."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import TranscriptStreamStatus
from models.transcript_stream import TranscriptStream


class TranscriptStreamRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, stream_id: UUID) -> TranscriptStream | None:
        result = await self._session.execute(
            select(TranscriptStream).where(TranscriptStream.id == stream_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, stream_id: UUID) -> TranscriptStream:
        row = await self.get_by_id(stream_id)
        if row is None:
            raise ValueError(f"TranscriptStream {stream_id} not found")
        return row

    async def get_for_update_or_raise(self, stream_id: UUID) -> TranscriptStream:
        """SELECT FOR UPDATE — holds row lock until transaction end."""
        result = await self._session.execute(
            select(TranscriptStream)
            .where(TranscriptStream.id == stream_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"TranscriptStream {stream_id} not found")
        return row

    async def get_by_key(self, stream_key: str) -> TranscriptStream | None:
        """Idempotency lookup."""
        result = await self._session.execute(
            select(TranscriptStream).where(TranscriptStream.stream_key == stream_key)
        )
        return result.scalar_one_or_none()

    async def get_by_transcript(
        self, transcript_id: UUID
    ) -> list[TranscriptStream]:
        result = await self._session.execute(
            select(TranscriptStream)
            .where(TranscriptStream.transcript_id == transcript_id)
            .order_by(TranscriptStream.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_active_for_transcript(
        self, transcript_id: UUID
    ) -> TranscriptStream | None:
        result = await self._session.execute(
            select(TranscriptStream).where(
                TranscriptStream.transcript_id == transcript_id,
                TranscriptStream.status == TranscriptStreamStatus.active,
            )
        )
        return result.scalar_one_or_none()
