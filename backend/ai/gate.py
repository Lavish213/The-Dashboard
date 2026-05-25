"""
AIApprovalGate — approval-gated AI action execution.

Before an AI execution may call a tool flagged requires_approval=True,
the gate creates an Approval row and pauses the execution (awaiting_approval).

On approval resolution:
  approved  → resume_from_approval() — execution continues
  rejected  → cancel execution with reason "approval_rejected"

This integrates with the existing Approval model and ApprovalRepository.
The AI execution side is handled by AIExecutionRuntime.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from ai.lifecycle import AIExecutionRuntime
from ai.registry import AIToolRegistry, ai_tool_registry
from models.approval import Approval
from models.enums import ApprovalStatus, ApprovalType, RiskLevel
from repositories.approval import ApprovalRepository

logger = structlog.get_logger(__name__)


class AIApprovalGateError(Exception):
    """Raised when an approval gate constraint cannot be satisfied."""


class AIApprovalGate:
    """
    Approval gate for AI tool invocations.

    check_tool() — inspect tool, create approval if required, pause execution.
    resolve()    — process approval decision, resume or cancel execution.
    """

    def __init__(
        self,
        session: AsyncSession,
        registry: AIToolRegistry | None = None,
    ) -> None:
        self._session = session
        self._registry = registry or ai_tool_registry
        self._approvals = ApprovalRepository(session)
        self._lifecycle = AIExecutionRuntime(session)

    async def check_tool(
        self,
        execution_id: UUID,
        tool_id: str,
        workflow_id: UUID | None = None,
        actor_id: UUID | None = None,
        risk_level: RiskLevel = RiskLevel.low,
    ) -> bool:
        """
        Check whether tool_id may proceed.

        Returns True  — tool may execute immediately.
        Returns False — execution paused, approval created. Caller must halt.
        """
        tool = self._registry.get(tool_id)
        if tool is None or not tool.requires_approval:
            return True

        if workflow_id is None:
            raise AIApprovalGateError(
                f"tool {tool_id!r} requires approval but no workflow_id provided"
            )

        approval_type = tool.approval_type or ApprovalType.outreach

        approval = Approval(
            workflow_id=workflow_id,
            approval_type=approval_type,
            approval_status=ApprovalStatus.pending,
            requested_by=actor_id,
            risk_level=risk_level,
        )
        self._session.add(approval)
        await self._session.flush()

        await self._lifecycle.mark_awaiting_approval(
            execution_id=execution_id,
            approval_id=approval.id,
        )

        logger.info(
            "ai.gate.approval_required",
            execution_id=str(execution_id),
            tool_id=tool_id,
            approval_id=str(approval.id),
        )
        return False

    async def resolve(
        self,
        execution_id: UUID,
        approval_id: UUID,
        approved: bool,
        resolved_by: UUID | None = None,
        notes: str = "",
    ) -> None:
        """
        Resolve a pending approval for an AI execution.

        approved=True  → resume_from_approval()
        approved=False → cancel execution with reason "approval_rejected"
        """
        approval = await self._approvals.get_for_update_or_raise(approval_id)
        if approval.approval_status not in (
            ApprovalStatus.pending,
            ApprovalStatus.escalated,
        ):
            raise AIApprovalGateError(
                f"approval {approval_id} is not resolvable (status={approval.approval_status})"
            )

        approval.approval_status = (
            ApprovalStatus.approved if approved else ApprovalStatus.rejected
        )
        approval.resolved_by = resolved_by
        approval.resolution_notes = notes
        self._session.add(approval)
        await self._session.flush()

        if approved:
            await self._lifecycle.resume_from_approval(execution_id)
            logger.info(
                "ai.gate.approved",
                execution_id=str(execution_id),
                approval_id=str(approval_id),
            )
        else:
            await self._lifecycle.cancel(execution_id, reason="approval_rejected")
            logger.info(
                "ai.gate.rejected",
                execution_id=str(execution_id),
                approval_id=str(approval_id),
            )
