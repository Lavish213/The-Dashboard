"""
AIExecutionContextAdapter — bridge AIExecution rows into ContextItems.

Converts AI execution state into a ContextItem summarizing the task type,
status, and output (if completed). Priority defaults to 3 (lowest domain layer).
"""
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from context.contracts import ContextItem
from models.ai_execution import AIExecution
from models.enums import ContextLayerType

_DEFAULT_PRIORITY = 3


class AIExecutionContextAdapter:
    """
    Load AI execution state and convert to ContextItems.

    load(execution_id) → list[ContextItem] (single item or empty list)
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def load(
        self,
        execution_id: UUID,
        priority: int = _DEFAULT_PRIORITY,
    ) -> list[ContextItem]:
        """
        Load AI execution and convert to a single ContextItem.

        Returns empty list if execution not found.
        """
        result = await self._session.execute(
            select(AIExecution).where(AIExecution.id == execution_id)
        )
        execution = result.scalar_one_or_none()
        if execution is None:
            return []

        content = (
            f"AI execution task={execution.task_type.value} "
            f"status={execution.status.value} "
            f"model={execution.model_name}"
        )
        if execution.output_payload:
            output_str = json.dumps(execution.output_payload)[:256]
            content += f" output={output_str}"

        return [
            ContextItem(
                layer=ContextLayerType.ai_execution,
                source_id=execution_id,
                source_type="ai_execution",
                content=content,
                token_count=max(1, len(content) // 4),
                priority=priority,
                created_at=execution.created_at,
                metadata={
                    "task_type": execution.task_type.value,
                    "status": execution.status.value,
                    "tokens_used": execution.tokens_used,
                },
            )
        ]
