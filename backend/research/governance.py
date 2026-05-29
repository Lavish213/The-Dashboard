"""
ResearchGovernanceRuntime — governance hook layer for research task actions.

Provides approval-compatible check points before task execution.
Does NOT implement orchestration logic — only evaluates policies.
Raises no exceptions on permit; raises ResearchGovernanceBlockedError on forbidden.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ResearchEventType
from repositories.governance_policy import GovernancePolicyRepository
from repositories.research_event import ResearchEventRepository
from research.contracts import ResearchGovernanceCheck, ResearchGovernanceResult

try:
    from governance.evaluator import (
        ActionClassification,
        PolicyEvaluationInput,
        PolicyEvaluator,
        RiskTier,
    )
    _EVALUATOR_AVAILABLE = True
except ImportError:
    _EVALUATOR_AVAILABLE = False


class ResearchGovernanceBlockedError(Exception):
    pass


class ResearchGovernanceRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._policies = GovernancePolicyRepository(session)
        self._events = ResearchEventRepository(session)
        self._evaluator = PolicyEvaluator() if _EVALUATOR_AVAILABLE else None

    async def check(
        self,
        check: ResearchGovernanceCheck,
    ) -> ResearchGovernanceResult:
        """
        Evaluate governance policy for a research task action.
        Emits governance_checked event.
        Raises ResearchGovernanceBlockedError if forbidden.
        """
        permitted = True
        requires_approval = False
        approval_id: UUID | None = None
        classification = "permitted"
        reason: str | None = None

        if self._evaluator is not None:
            policies = await self._policies.get_active()
            inp = PolicyEvaluationInput(
                action=check.action,
                risk_tier=RiskTier(check.risk_tier),
                actor_id=check.actor_id,
                context=check.context,
            )
            result = self._evaluator.evaluate(inp, policies)
            classification = result.classification.value
            permitted = result.classification not in (
                ActionClassification.forbidden,
            )
            requires_approval = result.classification == ActionClassification.restricted
            reason = result.reason
        else:
            # No evaluator available — default permit with note
            reason = "governance_evaluator_unavailable"

        await self._events.append(
            ResearchEventType.governance_checked,
            job_id=check.job_id,
            task_id=check.task_id,
            actor_id=check.actor_id,
            payload={
                "action": check.action,
                "classification": classification,
                "permitted": permitted,
                "requires_approval": requires_approval,
            },
        )

        if not permitted:
            raise ResearchGovernanceBlockedError(
                f"Action '{check.action}' blocked: {reason or classification}"
            )

        return ResearchGovernanceResult(
            action=check.action,
            permitted=permitted,
            requires_approval=requires_approval,
            approval_id=approval_id,
            classification=classification,
            reason=reason,
        )
