"""
EmergencyOverrideRuntime — emergency approval override infrastructure.

apply(override_key, approval_id, authorized_by, reason) — bypass normal approval.
  Idempotent on override_key.
  Immediately resolves the approval as approved.
  Mandatory audit entry — override cannot proceed without it.
"""
from __future__ import annotations

from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import EmergencyOverride
from models.enums import ApprovalStatus, GovernanceEventType
from repositories.approval import ApprovalRepository
from repositories.governance_event import GovernanceEventRepository


class OverrideError(Exception):
    pass


class EmergencyOverrideRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._approvals = ApprovalRepository(session)
        self._events = GovernanceEventRepository(session)

    async def apply(
        self,
        override_key: str,
        approval_id: UUID,
        authorized_by: UUID,
        reason: str,
    ) -> EmergencyOverride:
        """
        Apply an emergency override to approval_id.
        Idempotent on override_key.
        Immediately marks the approval as approved.
        Mandatory governance audit — always emits override_applied event.
        """
        # Idempotency check
        existing_events = await self._events.get_by_type(GovernanceEventType.override_applied)
        for evt in existing_events:
            if evt.payload.get("override_key") == override_key:
                return EmergencyOverride(
                    override_id=UUID(evt.payload["override_id"]),
                    override_key=override_key,
                    approval_id=UUID(evt.payload["approval_id"]),
                    authorized_by=UUID(evt.payload["authorized_by"]),
                    reason=evt.payload["reason"],
                    applied_at=evt.created_at,
                )

        approval = await self._approvals.get_for_update(approval_id)
        if approval is None:
            raise OverrideError(f"Approval {approval_id} not found")

        if approval.approval_status not in (
            ApprovalStatus.pending,
            ApprovalStatus.escalated,
        ):
            raise OverrideError(
                f"Cannot override approval {approval_id} in status {approval.approval_status}"
            )

        override_id = uuid4()

        # Resolve approval — resolved_by not set (override actor tracked in governance_events)
        from datetime import UTC, datetime
        approval.approval_status = ApprovalStatus.approved
        approval.resolution_notes = f"Emergency override: {reason}"
        self._session.add(approval)
        await self._session.flush()

        # Mandatory audit — always written, regardless of other state
        now = datetime.now(UTC)
        await self._events.append(
            event_type=GovernanceEventType.override_applied,
            approval_id=approval_id,
            actor_id=authorized_by,
            payload={
                "override_id": str(override_id),
                "override_key": override_key,
                "approval_id": str(approval_id),
                "authorized_by": str(authorized_by),
                "reason": reason,
                "applied_at": now.isoformat(),
            },
        )

        return EmergencyOverride(
            override_id=override_id,
            override_key=override_key,
            approval_id=approval_id,
            authorized_by=authorized_by,
            reason=reason,
            applied_at=now,
        )
