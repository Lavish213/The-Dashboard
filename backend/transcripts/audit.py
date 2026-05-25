"""
TranscriptAuditLinker — link transcripts to AI executions and audit log.

All linkage records are append-only writes to audit_logs table.
Retrieval queries audit_logs by transcript target_id.

link_execution()         — record that an AI execution processed this transcript.
get_linked_executions()  — list execution IDs linked to a transcript.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog
from models.enums import AuditActorType

_TARGET_TYPE = "transcript"
_ACTION_EXECUTION_LINKED = "transcript_execution_linked"
_ACTION_STREAM_LINKED = "transcript_stream_linked"


class TranscriptAuditLinker:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def link_execution(
        self,
        transcript_id: UUID,
        execution_id: UUID,
        actor_id: UUID | None = None,
    ) -> None:
        """
        Record that AI execution `execution_id` processed `transcript_id`.
        Append-only — duplicate links are allowed (idempotency is caller's concern).
        """
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=AuditActorType.ai,
            action=_ACTION_EXECUTION_LINKED,
            target_type=_TARGET_TYPE,
            target_id=transcript_id,
            payload={"execution_id": str(execution_id)},
        )
        self._session.add(entry)
        await self._session.flush()

    async def link_stream(
        self,
        transcript_id: UUID,
        stream_id: UUID,
        actor_id: UUID | None = None,
    ) -> None:
        """Record that stream `stream_id` belongs to `transcript_id`."""
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=AuditActorType.system,
            action=_ACTION_STREAM_LINKED,
            target_type=_TARGET_TYPE,
            target_id=transcript_id,
            payload={"stream_id": str(stream_id)},
        )
        self._session.add(entry)
        await self._session.flush()

    async def get_linked_executions(
        self, transcript_id: UUID
    ) -> list[UUID]:
        """Return execution UUIDs linked to this transcript, in recorded order."""
        result = await self._session.execute(
            select(AuditLog).where(
                AuditLog.target_type == _TARGET_TYPE,
                AuditLog.target_id == transcript_id,
                AuditLog.action == _ACTION_EXECUTION_LINKED,
            ).order_by(AuditLog.created_at.asc())
        )
        return [
            UUID(row.payload["execution_id"])
            for row in result.scalars().all()
        ]

    async def get_linked_streams(
        self, transcript_id: UUID
    ) -> list[UUID]:
        """Return stream UUIDs linked to this transcript, in recorded order."""
        result = await self._session.execute(
            select(AuditLog).where(
                AuditLog.target_type == _TARGET_TYPE,
                AuditLog.target_id == transcript_id,
                AuditLog.action == _ACTION_STREAM_LINKED,
            ).order_by(AuditLog.created_at.asc())
        )
        return [
            UUID(row.payload["stream_id"])
            for row in result.scalars().all()
        ]
