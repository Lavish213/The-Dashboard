"""
AIAuditRuntime — append-only audit trail for AI executions.

Writes to audit_logs table with actor_type=ai.
All entries are immutable after creation — no updates, no deletes.

Records: execution lifecycle transitions, tool invocations, approval gates,
budget events, cancellations.
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

_TARGET_TYPE = "ai_execution"


@dataclass(frozen=True)
class AIAuditEntry:
    """Immutable view of one audit_log row for an AI execution."""

    entry_id: UUID
    execution_id: UUID
    action: str
    payload: dict
    actor_id: UUID | None
    recorded_at: datetime


class AIAuditRuntime:
    """
    Append-only AI audit log.

    record() — append one entry. Never mutates existing rows.
    get_for_execution() — ordered history for forensic analysis.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        execution_id: UUID,
        action: str,
        payload: dict | None = None,
        actor_id: UUID | None = None,
    ) -> AIAuditEntry:
        """
        Append an audit entry for execution_id.
        action — e.g. "execution_started", "tool_called", "budget_consumed".
        """
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=AuditActorType.ai,
            action=action,
            target_type=_TARGET_TYPE,
            target_id=execution_id,
            payload=payload or {},
        )
        self._session.add(entry)
        await self._session.flush()

        logger.info(
            "ai.audit.recorded",
            execution_id=str(execution_id),
            action=action,
        )

        return AIAuditEntry(
            entry_id=entry.id,
            execution_id=execution_id,
            action=action,
            payload=payload or {},
            actor_id=actor_id,
            recorded_at=entry.created_at,
        )

    async def get_for_execution(
        self, execution_id: UUID
    ) -> list[AIAuditEntry]:
        """Return all audit entries for execution_id, oldest first."""
        result = await self._session.execute(
            select(AuditLog)
            .where(
                AuditLog.target_type == _TARGET_TYPE,
                AuditLog.target_id == execution_id,
                AuditLog.actor_type == AuditActorType.ai,
            )
            .order_by(AuditLog.created_at.asc())
        )
        return [
            AIAuditEntry(
                entry_id=row.id,
                execution_id=execution_id,
                action=row.action,
                payload=row.payload,
                actor_id=row.actor_id,
                recorded_at=row.created_at,
            )
            for row in result.scalars().all()
        ]
