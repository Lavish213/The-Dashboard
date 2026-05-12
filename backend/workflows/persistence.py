from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import AuditActorType, WorkflowStatus
from models.workflow import Workflow
from models.workflow_event import WorkflowEvent
from repositories.base import BaseRepository, PageResult


class WorkflowRepository(BaseRepository[Workflow]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, Workflow)

    async def get_for_update(self, workflow_id: UUID) -> Workflow | None:
        """Fetch workflow with SELECT FOR UPDATE — holds row lock until transaction end."""
        result = await self.session.execute(
            select(Workflow).where(Workflow.id == workflow_id).with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_for_update_or_raise(self, workflow_id: UUID) -> Workflow:
        from core.exceptions import NotFoundError
        workflow = await self.get_for_update(workflow_id)
        if workflow is None:
            raise NotFoundError(Workflow.__tablename__, str(workflow_id))
        return workflow

    async def get_by_correlation_id(self, correlation_id: UUID) -> Workflow | None:
        result = await self.session.execute(
            select(Workflow).where(Workflow.correlation_id == correlation_id)
        )
        return result.scalar_one_or_none()

    async def get_active(self, page: int = 1, page_size: int = 20) -> PageResult[Workflow]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Workflow.workflow_status == WorkflowStatus.active],
            order_by=Workflow.created_at.desc(),
        )

    async def get_by_lead(self, lead_id: UUID, page: int = 1, page_size: int = 20) -> PageResult[Workflow]:
        return await self.list_paginated(
            page=page, page_size=page_size,
            filters=[Workflow.lead_id == lead_id],
            order_by=Workflow.created_at.desc(),
        )

class WorkflowEventRepository(BaseRepository[WorkflowEvent]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, WorkflowEvent)

    async def get_by_workflow(self, workflow_id: UUID) -> list[WorkflowEvent]:
        result = await self.session.execute(
            select(WorkflowEvent)
            .where(WorkflowEvent.workflow_id == workflow_id)
            .order_by(WorkflowEvent.created_at.asc(), WorkflowEvent.id.asc())
        )
        return list(result.scalars().all())

    async def append_event(
        self,
        workflow_id: UUID,
        event_type: str,
        payload: dict,
        actor_type: AuditActorType,
        actor_id: UUID | None,
        correlation_id: UUID,
        causation_id: UUID | None = None,
    ) -> WorkflowEvent:
        return await self.create(
            workflow_id=workflow_id,
            event_type=event_type,
            payload=payload,
            actor_type=actor_type,
            actor_id=actor_id,
            correlation_id=correlation_id,
            causation_id=causation_id,
        )
