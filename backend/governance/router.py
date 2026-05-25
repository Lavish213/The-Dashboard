"""
ApprovalRouter — route approval requests based on policy evaluation results.

route(evaluation_result, approval_id) — record routing decision, emit event.
resolve_delegate(actor_id, approval_type, risk_tier) — check if actor is acting
  as a delegate for someone else; return effective approver UUID.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import ApprovalRoute, PolicyEvaluationResult
from models.enums import ApprovalType, GovernanceEventType, RiskTier
from repositories.approval_delegation import ApprovalDelegationRepository
from repositories.governance_event import GovernanceEventRepository


class ApprovalRouter:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._events = GovernanceEventRepository(session)
        self._delegations = ApprovalDelegationRepository(session)

    async def route(
        self,
        evaluation: PolicyEvaluationResult,
        approval_id: UUID,
        actor_id: UUID | None = None,
    ) -> ApprovalRoute:
        """
        Record routing decision for approval_id based on evaluation result.
        Emits a governance_event of type approval_routed.
        Returns ApprovalRoute.
        """
        route = ApprovalRoute(
            approval_id=approval_id,
            routing_strategy=evaluation.routing_strategy,
            approver_ids=evaluation.approver_ids,
            escalation_chain=evaluation.escalation_chain,
            quorum_required=evaluation.quorum_required,
            timeout_seconds=evaluation.timeout_seconds,
            escalation_timeout_seconds=60,  # default; policies can override
        )

        await self._events.append(
            event_type=GovernanceEventType.approval_routed,
            approval_id=approval_id,
            actor_id=actor_id,
            payload={
                "routing_strategy": evaluation.routing_strategy.value,
                "approver_ids": [str(uid) for uid in evaluation.approver_ids],
                "quorum_required": evaluation.quorum_required,
                "matched_policy_key": evaluation.matched_policy_key,
                "matched_policy_version": evaluation.matched_policy_version,
            },
        )
        return route

    async def resolve_delegate(
        self,
        actor_id: UUID,
        approval_type: ApprovalType,
        risk_tier: RiskTier,
    ) -> UUID:
        """
        If actor_id has active delegations scoped to this approval_type and risk_tier,
        return the delegator's UUID (the actor is acting on behalf of delegator).
        Otherwise return actor_id unchanged.

        Only returns first matching delegation (delegations are ordered by created_at).
        """
        delegations = await self._delegations.get_active_for_delegate(actor_id)
        for delegation in delegations:
            type_ok = (
                not delegation.approval_types
                or approval_type.value in delegation.approval_types
            )
            tier_ok = (
                not delegation.risk_tiers
                or risk_tier.value in delegation.risk_tiers
            )
            if type_ok and tier_ok:
                return delegation.delegator_id
        return actor_id
