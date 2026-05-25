"""
ResearchAuditRuntime — audit logging for research job/task lifecycle.

Writes to audit_logs with target_type="research".
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog
from models.enums import AuditActorType


@dataclass(frozen=True)
class ResearchAuditEntry:
    audit_id: UUID
    action: str
    target_id: UUID | None
    actor_id: UUID | None
    actor_type: AuditActorType
    payload: dict
    recorded_at: datetime


class ResearchAuditRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        action: str,
        target_id: UUID | None = None,
        payload: dict | None = None,
        actor_id: UUID | None = None,
        actor_type: AuditActorType = AuditActorType.system,
    ) -> ResearchAuditEntry:
        """Write an audit log entry for a research runtime action."""
        row = AuditLog(
            action=action,
            target_type="research",
            target_id=target_id,
            actor_id=actor_id,
            actor_type=actor_type,
            payload=payload or {},
        )
        self._session.add(row)
        await self._session.flush()

        return ResearchAuditEntry(
            audit_id=row.id,
            action=action,
            target_id=target_id,
            actor_id=actor_id,
            actor_type=actor_type,
            payload=payload or {},
            recorded_at=row.created_at,
        )

    async def get_for_target(self, target_id: UUID) -> list[ResearchAuditEntry]:
        result = await self._session.execute(
            select(AuditLog)
            .where(
                AuditLog.target_type == "research",
                AuditLog.target_id == target_id,
            )
            .order_by(AuditLog.created_at)
        )
        rows = result.scalars().all()
        return [
            ResearchAuditEntry(
                audit_id=r.id,
                action=r.action,
                target_id=r.target_id,
                actor_id=r.actor_id,
                actor_type=r.actor_type,
                payload=r.payload or {},
                recorded_at=r.created_at,
            )
            for r in rows
        ]
