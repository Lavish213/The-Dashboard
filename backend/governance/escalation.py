"""
EscalationChainRuntime — approval escalation chain + timeout handling.

escalate(approval_id, route, step_index) — trigger one escalation step.
check_timeout(approval_id, route, created_at) — check if timeout exceeded.
get_current_step(approval_id, chain) — current escalation depth from event log.
"""
from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import ApprovalRoute, EscalationStep
from models.enums import ApprovalStatus, GovernanceEventType
from repositories.approval import ApprovalRepository
from repositories.governance_event import GovernanceEventRepository


class EscalationError(Exception):
    pass


class EscalationChainRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = GovernanceEventRepository(session)
        self._approvals = ApprovalRepository(session)

    async def escalate(
        self,
        approval_id: UUID,
        step: EscalationStep,
        step_index: int,
        actor_id: UUID | None = None,
    ) -> None:
        """
        Trigger one escalation step. Updates approval_status → escalated.
        Emits escalation_triggered event.
        """
        approval = await self._approvals.get_for_update(approval_id)
        if approval is None:
            raise EscalationError(f"Approval {approval_id} not found")

        if approval.approval_status not in (
            ApprovalStatus.pending,
            ApprovalStatus.escalated,
        ):
            raise EscalationError(
                f"Cannot escalate approval {approval_id} in status {approval.approval_status}"
            )

        approval.approval_status = ApprovalStatus.escalated
        self._session.add(approval)
        await self._session.flush()

        await self._events.append(
            event_type=GovernanceEventType.escalation_triggered,
            approval_id=approval_id,
            actor_id=actor_id,
            payload={
                "step_index": step_index,
                "escalate_to": str(step.escalate_to),
                "after_seconds": step.after_seconds,
                "reason": step.reason,
            },
        )

    async def check_timeout(
        self,
        approval_id: UUID,
        route: ApprovalRoute,
        created_at: datetime,
    ) -> bool:
        """
        Return True if approval has exceeded its timeout (route.timeout_seconds).
        Does NOT trigger escalation — caller must call escalate() if True.
        """
        elapsed = (datetime.now(UTC) - created_at).total_seconds()
        return elapsed > route.timeout_seconds

    async def get_current_step(
        self,
        approval_id: UUID,
        chain: tuple[EscalationStep, ...],
    ) -> int:
        """
        Return the current escalation step index (0-based) by counting
        escalation_triggered events for approval_id.
        Returns len(chain) if fully escalated.
        """
        events = await self._events.get_for_approval(approval_id)
        count = sum(
            1 for e in events
            if e.event_type == GovernanceEventType.escalation_triggered
        )
        return min(count, len(chain))

    async def resolve_escalation(
        self,
        approval_id: UUID,
        actor_id: UUID | None = None,
        resolution: str = "resolved",
    ) -> None:
        """Mark escalation resolved — emits escalation_resolved event."""
        await self._events.append(
            event_type=GovernanceEventType.escalation_resolved,
            approval_id=approval_id,
            actor_id=actor_id,
            payload={"resolution": resolution},
        )
