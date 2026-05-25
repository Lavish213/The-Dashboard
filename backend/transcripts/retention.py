"""
TranscriptRetentionRuntime — runtime-safe retention policy enforcement.

Retention actions:
  archive()    — move transcript to archived status (append-only, reversible for recovery).
  soft_delete()— set deleted_at (via TimestampMixin). Excludes from normal queries.
  find_expired()  — find transcripts past their retention threshold.
  find_archivable()  — find transcripts eligible for archival.

No hard deletes. No cascades. Append-only audit preserved.
`requires_explicit_delete` policy flag blocks auto-deletion.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import TranscriptStatus
from models.transcript import Transcript
from transcripts.contracts import RetentionPolicy
from transcripts.repositories.transcript import TranscriptRepository
from transcripts.runtime.runtime import TranscriptRuntime

logger = structlog.get_logger(__name__)


class RetentionViolationError(Exception):
    """Raised when a retention policy blocks an operation."""


class TranscriptRetentionRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = TranscriptRepository(session)
        self._runtime = TranscriptRuntime(session)

    async def archive(
        self,
        transcript_id: UUID,
        policy: RetentionPolicy | None = None,
    ) -> None:
        """
        Archive transcript if not already archived.
        No-op if already archived.
        """
        transcript = await self._repo.get_by_id_or_raise(transcript_id)
        if transcript.transcript_status == TranscriptStatus.archived:
            return
        await self._runtime.archive(transcript_id)
        logger.info("transcript.archived", transcript_id=str(transcript_id))

    async def soft_delete(
        self,
        transcript_id: UUID,
        policy: RetentionPolicy | None = None,
    ) -> None:
        """
        Soft-delete transcript by setting deleted_at.
        Raises RetentionViolationError if policy blocks explicit delete.
        """
        if policy and policy.requires_explicit_delete:
            raise RetentionViolationError(
                f"transcript {transcript_id} requires explicit delete; "
                "set requires_explicit_delete=False to proceed"
            )

        transcript = await self._repo.get_for_update_or_raise(transcript_id)
        if transcript.deleted_at is not None:
            return  # already soft-deleted

        transcript.deleted_at = datetime.now(UTC)
        self._session.add(transcript)
        await self._session.flush()
        logger.info("transcript.soft_deleted", transcript_id=str(transcript_id))

    async def find_expired(
        self,
        delete_after_days: int,
        now: datetime | None = None,
    ) -> list[UUID]:
        """
        Return IDs of completed/archived transcripts older than delete_after_days.
        Only includes not-yet-soft-deleted rows.
        """
        cutoff = (now or datetime.now(UTC)) - timedelta(days=delete_after_days)
        result = await self._session.execute(
            select(Transcript.id).where(
                Transcript.created_at < cutoff,
                Transcript.deleted_at.is_(None),
                Transcript.transcript_status.in_([
                    TranscriptStatus.completed,
                    TranscriptStatus.archived,
                ]),
            )
        )
        return [row[0] for row in result.all()]

    async def find_archivable(
        self,
        archive_after_days: int,
        now: datetime | None = None,
    ) -> list[UUID]:
        """
        Return IDs of completed transcripts older than archive_after_days.
        Excludes already-archived and soft-deleted rows.
        """
        cutoff = (now or datetime.now(UTC)) - timedelta(days=archive_after_days)
        result = await self._session.execute(
            select(Transcript.id).where(
                Transcript.created_at < cutoff,
                Transcript.deleted_at.is_(None),
                Transcript.transcript_status == TranscriptStatus.completed,
            )
        )
        return [row[0] for row in result.all()]
