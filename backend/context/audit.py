"""
ContextAuditRuntime — append-only audit trail for context assembly operations.

Writes to audit_logs with actor_type=system, target_type="context_snapshot".
All entries immutable after creation.

Records: snapshot created, snapshot archived, snapshot expired,
         guardrail violations, cache hits.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog
from models.enums import AuditActorType

logger = structlog.get_logger(__name__)

_TARGET_TYPE = "context_snapshot"

ACTION_SNAPSHOT_CREATED = "context_snapshot_created"
ACTION_SNAPSHOT_ARCHIVED = "context_snapshot_archived"
ACTION_SNAPSHOT_EXPIRED = "context_snapshot_expired"
ACTION_GUARDRAIL_VIOLATION = "context_guardrail_violation"
ACTION_CACHE_HIT = "context_cache_hit"
ACTION_ASSEMBLY_COMPLETED = "context_assembly_completed"


@dataclass(frozen=True)
class ContextAuditEntry:
    entry_id: UUID
    snapshot_id: UUID | None
    action: str
    payload: dict
    actor_id: UUID | None
    recorded_at: datetime


class ContextAuditRuntime:
    """Append-only context audit log."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        action: str,
        snapshot_id: UUID | None = None,
        payload: dict | None = None,
        actor_id: UUID | None = None,
    ) -> ContextAuditEntry:
        """Append one audit entry."""
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=AuditActorType.system,
            action=action,
            target_type=_TARGET_TYPE,
            target_id=snapshot_id,
            payload=payload or {},
        )
        self._session.add(entry)
        await self._session.flush()

        logger.info(
            "context.audit.recorded",
            action=action,
            snapshot_id=str(snapshot_id) if snapshot_id else None,
        )

        return ContextAuditEntry(
            entry_id=entry.id,
            snapshot_id=snapshot_id,
            action=action,
            payload=payload or {},
            actor_id=actor_id,
            recorded_at=entry.created_at,
        )

    async def get_for_snapshot(self, snapshot_id: UUID) -> list[ContextAuditEntry]:
        """Return all audit entries for snapshot_id, oldest first."""
        result = await self._session.execute(
            select(AuditLog)
            .where(
                AuditLog.target_type == _TARGET_TYPE,
                AuditLog.target_id == snapshot_id,
            )
            .order_by(AuditLog.created_at.asc())
        )
        return [
            ContextAuditEntry(
                entry_id=row.id,
                snapshot_id=snapshot_id,
                action=row.action,
                payload=row.payload,
                actor_id=row.actor_id,
                recorded_at=row.created_at,
            )
            for row in result.scalars().all()
        ]
