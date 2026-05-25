"""
TranscriptTokenTracker — aggregate token usage from stream sessions.

Reads from transcript_streams rows. Read-only aggregation — no mutations.
Call after streams are complete for accurate totals.

total_for_transcript() — sums all streams for a transcript.
total_for_stream()     — usage for one stream.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models.transcript_stream import TranscriptStream
from transcripts.contracts import TokenUsage


class TranscriptTokenTracker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total_for_transcript(self, transcript_id: UUID) -> TokenUsage:
        """Sum token usage across all streams for this transcript."""
        result = await self._session.execute(
            select(
                func.coalesce(func.sum(TranscriptStream.tokens_input), 0),
                func.coalesce(func.sum(TranscriptStream.tokens_output), 0),
            ).where(TranscriptStream.transcript_id == transcript_id)
        )
        row = result.one()
        return TokenUsage(tokens_input=int(row[0]), tokens_output=int(row[1]))

    async def total_for_stream(self, stream_id: UUID) -> TokenUsage:
        """Token usage for a single stream."""
        result = await self._session.execute(
            select(TranscriptStream.tokens_input, TranscriptStream.tokens_output)
            .where(TranscriptStream.id == stream_id)
        )
        row = result.one_or_none()
        if row is None:
            return TokenUsage(tokens_input=0, tokens_output=0)
        return TokenUsage(
            tokens_input=int(row[0] or 0),
            tokens_output=int(row[1] or 0),
        )
