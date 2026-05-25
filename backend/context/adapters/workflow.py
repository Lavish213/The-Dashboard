"""
WorkflowContextAdapter — bridge Workflow rows into ContextItems.

Converts workflow state into a single ContextItem summarizing the
current step, status, and type. Priority defaults to 2 (below transcript).
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from context.contracts import ContextItem
from models.enums import ContextLayerType
from models.workflow import Workflow

_DEFAULT_PRIORITY = 2


class WorkflowContextAdapter:
    """
    Load workflow state and convert to a ContextItem.

    load(workflow_id) → list[ContextItem] (single item or empty list)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(
        self,
        workflow_id: UUID,
        priority: int = _DEFAULT_PRIORITY,
    ) -> list[ContextItem]:
        """
        Load workflow and convert to a single ContextItem.

        Returns empty list if workflow not found.
        """
        result = await self._session.execute(
            select(Workflow).where(Workflow.id == workflow_id)
        )
        workflow = result.scalar_one_or_none()
        if workflow is None:
            return []

        content = (
            f"Workflow type={workflow.workflow_type.value} "
            f"status={workflow.workflow_status.value}"
        )
        if workflow.current_step:
            content += f" step={workflow.current_step}"

        return [
            ContextItem(
                layer=ContextLayerType.workflow,
                source_id=workflow_id,
                source_type="workflow",
                content=content,
                token_count=max(1, len(content) // 4),
                priority=priority,
                created_at=workflow.created_at,
                metadata={
                    "workflow_type": workflow.workflow_type.value,
                    "status": workflow.workflow_status.value,
                    "current_step": workflow.current_step,
                },
            )
        ]
