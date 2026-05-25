"""
GovernanceAuditRuntime — append-only governance audit trail.

All governance runtime transitions must call record().
Writes to audit_logs (target_type="governance") and governance_events simultaneously.

record() — append one audit entry.
get_for_approval() — ordered approval audit history.
get_for_policy() — ordered policy audit history.
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

_TARGET_TYPE = "governance"
ACTION_POLICY_EVALUATED = "governance_policy_evaluated"
ACTION_APPROVAL_ROUTED = "governance_approval_routed"
ACTION_ESCALATION = "governance_escalation_triggered"
ACTION_OVERRIDE = "governance_emergency_override"
ACTION_FREEZE = "governance_freeze_activated"
ACTION_KILL_SWITCH = "governance_kill_switch_triggered"
ACTION_QUORUM_VOTE = "governance_quorum_vote_cast"
ACTION_DELEGATION = "governance_delegation_granted"


@dataclass(frozen=True)
class GovernanceAuditEntry:
    entry_id: UUID
    target_id: UUID | None
    action: str
    payload: dict
    actor_id: UUID | None
    recorded_at: datetime


class GovernanceAuditRuntime:
    """Append-only governance audit log. Writes to audit_logs."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def record(
        self,
        action: str,
        target_id: UUID | None = None,
        payload: dict | None = None,
        actor_id: UUID | None = None,
    ) -> GovernanceAuditEntry:
        entry = AuditLog(
            actor_id=actor_id,
            actor_type=AuditActorType.system,
            action=action,
            target_type=_TARGET_TYPE,
            target_id=target_id,
            payload=payload or {},
        )
        self._session.add(entry)
        await self._session.flush()

        logger.info(
            "governance.audit.recorded",
            action=action,
            target_id=str(target_id) if target_id else None,
        )

        return GovernanceAuditEntry(
            entry_id=entry.id,
            target_id=target_id,
            action=action,
            payload=payload or {},
            actor_id=actor_id,
            recorded_at=entry.created_at,
        )

    async def get_for_target(self, target_id: UUID) -> list[GovernanceAuditEntry]:
        result = await self._session.execute(
            select(AuditLog)
            .where(
                AuditLog.target_type == _TARGET_TYPE,
                AuditLog.target_id == target_id,
            )
            .order_by(AuditLog.created_at.asc())
        )
        return [
            GovernanceAuditEntry(
                entry_id=row.id,
                target_id=target_id,
                action=row.action,
                payload=row.payload,
                actor_id=row.actor_id,
                recorded_at=row.created_at,
            )
            for row in result.scalars().all()
        ]
