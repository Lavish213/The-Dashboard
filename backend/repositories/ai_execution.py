"""
AIExecutionRepository — data access for AI execution rows.

Provides SELECT FOR UPDATE for safe status transitions.
get_by_key — idempotency lookup before creating new executions.
"""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.ai_execution import AIExecution
from models.enums import AIExecutionStatus


class AIExecutionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, execution_id: UUID) -> AIExecution | None:
        result = await self._session.execute(
            select(AIExecution).where(AIExecution.id == execution_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_or_raise(self, execution_id: UUID) -> AIExecution:
        row = await self.get_by_id(execution_id)
        if row is None:
            raise ValueError(f"AIExecution {execution_id} not found")
        return row

    async def get_for_update_or_raise(self, execution_id: UUID) -> AIExecution:
        """SELECT FOR UPDATE — holds row lock until transaction end."""
        result = await self._session.execute(
            select(AIExecution)
            .where(AIExecution.id == execution_id)
            .with_for_update()
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ValueError(f"AIExecution {execution_id} not found")
        return row

    async def get_by_key(self, execution_key: str) -> AIExecution | None:
        """Idempotency lookup — returns existing execution for this key."""
        result = await self._session.execute(
            select(AIExecution).where(AIExecution.execution_key == execution_key)
        )
        return result.scalar_one_or_none()

    async def get_by_workflow(self, workflow_id: UUID) -> list[AIExecution]:
        result = await self._session.execute(
            select(AIExecution)
            .where(AIExecution.workflow_id == workflow_id)
            .order_by(AIExecution.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_status(self, status: AIExecutionStatus) -> list[AIExecution]:
        result = await self._session.execute(
            select(AIExecution)
            .where(AIExecution.status == status)
            .order_by(AIExecution.created_at.asc())
        )
        return list(result.scalars().all())
