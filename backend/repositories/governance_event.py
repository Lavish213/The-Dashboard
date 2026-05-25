"""GovernanceEventRepository — append-only governance event log."""
from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import GovernanceEventType
from models.governance_event import GovernanceEvent
from repositories.base import BaseRepository


class GovernanceEventRepository(BaseRepository[GovernanceEvent]):
    def __init__(self, session: AsyncSession) -> None:
        super().__init__(session, GovernanceEvent)

    async def append(
        self,
        event_type: GovernanceEventType,
        payload: dict,
        policy_id: UUID | None = None,
        approval_id: UUID | None = None,
        actor_id: UUID | None = None,
        correlation_id: UUID | None = None,
    ) -> GovernanceEvent:
        """Append one immutable governance event."""
        return await self.create(
            event_type=event_type,
            payload=payload,
            policy_id=policy_id,
            approval_id=approval_id,
            actor_id=actor_id,
            correlation_id=correlation_id,
        )

    async def get_for_approval(self, approval_id: UUID) -> list[GovernanceEvent]:
        """Return all events for approval_id, oldest first."""
        result = await self.session.execute(
            select(GovernanceEvent)
            .where(GovernanceEvent.approval_id == approval_id)
            .order_by(GovernanceEvent.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_for_policy(self, policy_id: UUID) -> list[GovernanceEvent]:
        """Return all events for policy_id, oldest first."""
        result = await self.session.execute(
            select(GovernanceEvent)
            .where(GovernanceEvent.policy_id == policy_id)
            .order_by(GovernanceEvent.created_at.asc())
        )
        return list(result.scalars().all())

    async def get_by_type(self, event_type: GovernanceEventType) -> list[GovernanceEvent]:
        """Return all events of a given type, oldest first."""
        result = await self.session.execute(
            select(GovernanceEvent)
            .where(GovernanceEvent.event_type == event_type)
            .order_by(GovernanceEvent.created_at.asc())
        )
        return list(result.scalars().all())
