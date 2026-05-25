"""
GovernanceMetricsRuntime — governance metrics primitives.

Computes metrics from governance_events and approval tables via SQL aggregation.
All metrics are read-only — no state mutations.

compute(period_start, period_end) → GovernanceMetrics
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import GovernanceMetrics
from models.approval import Approval
from models.approval_delegation import ApprovalDelegation
from models.enums import (
    ApprovalStatus,
    DelegationStatus,
    GovernanceEventType,
)
from models.governance_event import GovernanceEvent


class GovernanceMetricsRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def compute(
        self,
        period_start: datetime,
        period_end: datetime,
    ) -> GovernanceMetrics:
        """
        Aggregate governance metrics over [period_start, period_end].
        """
        total_evaluations = await self._count_events(
            GovernanceEventType.policy_evaluated, period_start, period_end
        )
        escalations = await self._count_events(
            GovernanceEventType.escalation_triggered, period_start, period_end
        )
        overrides = await self._count_events(
            GovernanceEventType.override_applied, period_start, period_end
        )
        freeze_events = await self._count_events(
            GovernanceEventType.freeze_activated, period_start, period_end
        )

        # Approvals pending
        pending_result = await self._session.execute(
            select(func.count()).select_from(Approval).where(
                Approval.approval_status == ApprovalStatus.pending,
                Approval.created_at >= period_start,
                Approval.created_at <= period_end,
            )
        )
        approvals_pending = pending_result.scalar_one()

        # Approvals resolved (approved + rejected + expired)
        resolved_result = await self._session.execute(
            select(func.count()).select_from(Approval).where(
                Approval.approval_status.in_([
                    ApprovalStatus.approved,
                    ApprovalStatus.rejected,
                    ApprovalStatus.expired,
                ]),
                Approval.created_at >= period_start,
                Approval.created_at <= period_end,
            )
        )
        approvals_resolved = resolved_result.scalar_one()

        # Active delegations
        deleg_result = await self._session.execute(
            select(func.count()).select_from(ApprovalDelegation).where(
                ApprovalDelegation.status == DelegationStatus.active,
            )
        )
        delegations_active = deleg_result.scalar_one()

        return GovernanceMetrics(
            total_evaluations=total_evaluations,
            approvals_pending=approvals_pending,
            approvals_resolved=approvals_resolved,
            escalations_triggered=escalations,
            overrides_applied=overrides,
            freeze_events=freeze_events,
            delegations_active=delegations_active,
            period_start=period_start,
            period_end=period_end,
        )

    async def _count_events(
        self,
        event_type: GovernanceEventType,
        period_start: datetime,
        period_end: datetime,
    ) -> int:
        result = await self._session.execute(
            select(func.count()).select_from(GovernanceEvent).where(
                GovernanceEvent.event_type == event_type,
                GovernanceEvent.created_at >= period_start,
                GovernanceEvent.created_at <= period_end,
            )
        )
        return result.scalar_one()
