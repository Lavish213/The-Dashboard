"""
SophiaToolBoundary — tool permission boundary + governance-gated Sophia actions.

Checks tool calls against the governance policy evaluator before permitting
execution. Forbidden actions are blocked immediately. Restricted/Privileged
actions require approval before execution proceeds.

This is infrastructure only — no actual tool implementations.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from governance.contracts import PolicyEvaluationInput
from governance.evaluator import PolicyEvaluator
from models.enums import ActionClassification, RiskTier, SophiaEventType
from repositories.governance_policy import GovernancePolicyRepository
from repositories.sophia_event import SophiaEventRepository
from sophia.contracts import SophiaToolPermissionRequest, SophiaToolPermissionResult


class SophiaToolBoundary:
    """
    Evaluate tool calls against governance policies.
    Emits tool_permitted / tool_blocked events.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._policies = GovernancePolicyRepository(session)
        self._evaluator = PolicyEvaluator()
        self._events = SophiaEventRepository(session)

    async def check(
        self,
        request: SophiaToolPermissionRequest,
    ) -> SophiaToolPermissionResult:
        """
        Evaluate whether a tool action is permitted.
        Returns SophiaToolPermissionResult with classification verdict.
        """
        policies = await self._policies.get_active()
        inp = PolicyEvaluationInput(
            action=request.action,
            risk_tier=RiskTier(request.risk_tier),
            actor_id=request.actor_id,
            context=request.context,
        )
        result = self._evaluator.evaluate(inp, policies)

        permitted = result.classification not in (
            ActionClassification.forbidden,
        )
        requires_approval = result.requires_approval

        event_type = (
            SophiaEventType.tool_permitted if permitted
            else SophiaEventType.tool_blocked
        )
        await self._events.append(
            event_type,
            session_id=request.session_id,
            turn_id=request.turn_id,
            actor_id=request.actor_id,
            payload={
                "tool_name": request.tool_name,
                "action": request.action,
                "classification": result.classification.value,
                "requires_approval": requires_approval,
                "evaluation_id": result.evaluation_id,
            },
        )

        if requires_approval:
            await self._events.append(
                SophiaEventType.governance_evaluated,
                session_id=request.session_id,
                turn_id=request.turn_id,
                actor_id=request.actor_id,
                payload={
                    "action": request.action,
                    "classification": result.classification.value,
                    "routing_strategy": result.routing_strategy.value,
                    "evaluation_id": result.evaluation_id,
                },
            )

        return SophiaToolPermissionResult(
            tool_name=request.tool_name,
            action=request.action,
            permitted=permitted,
            requires_approval=requires_approval,
            approval_id=None,  # Caller creates approval via governance router
            classification=result.classification.value,
            reason=(
                f"Policy evaluation: {result.classification.value}"
                if not permitted
                else None
            ),
        )
