"""TranscriptCheckpoint repository — append-only, position-ordered."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from models.transcript_checkpoint import TranscriptCheckpoint


class TranscriptCheckpointRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_latest(
        self, transcript_id: UUID
    ) -> TranscriptCheckpoint | None:
        result = await self._session.execute(
            select(TranscriptCheckpoint)
            .where(TranscriptCheckpoint.transcript_id == transcript_id)
            .order_by(TranscriptCheckpoint.chunk_index.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_for_stream(
        self, stream_id: UUID
    ) -> list[TranscriptCheckpoint]:
        result = await self._session.execute(
            select(TranscriptCheckpoint)
            .where(TranscriptCheckpoint.stream_id == stream_id)
            .order_by(TranscriptCheckpoint.chunk_index.asc())
        )
        return list(result.scalars().all())

    async def get_all(
        self, transcript_id: UUID
    ) -> list[TranscriptCheckpoint]:
        result = await self._session.execute(
            select(TranscriptCheckpoint)
            .where(TranscriptCheckpoint.transcript_id == transcript_id)
            .order_by(TranscriptCheckpoint.chunk_index.asc())
        )
        return list(result.scalars().all())

    async def set(
        self,
        transcript_id: UUID,
        chunk_index: int,
        state: dict | None = None,
        stream_id: UUID | None = None,
        label: str | None = None,
    ) -> TranscriptCheckpoint:
        """
        Idempotent: if (transcript_id, chunk_index) already exists, return it.
        """
        existing = await self._get_by_position(transcript_id, chunk_index)
        if existing is not None:
            return existing

        cp = TranscriptCheckpoint(
            transcript_id=transcript_id,
            stream_id=stream_id,
            chunk_index=chunk_index,
            state=state or {},
            label=label,
        )
        self._session.add(cp)
        try:
            await self._session.flush()
        except IntegrityError:
            await self._session.rollback()
            existing = await self._get_by_position(transcript_id, chunk_index)
            if existing is None:
                raise
            return existing
        return cp

    async def _get_by_position(
        self, transcript_id: UUID, chunk_index: int
    ) -> TranscriptCheckpoint | None:
        result = await self._session.execute(
            select(TranscriptCheckpoint).where(
                TranscriptCheckpoint.transcript_id == transcript_id,
                TranscriptCheckpoint.chunk_index == chunk_index,
            )
        )
        return result.scalar_one_or_none()
