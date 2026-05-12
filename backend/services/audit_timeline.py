"""
AuditTimelineRuntime — append-only audit log with cross-entity timeline feed.

Responsibilities:
- append: write an audit event (actor, action, target, payload)
- get_timeline: paginated unified feed across all entities
- get_by_target / get_by_actor / get_by_correlation: filtered views
- realtime broadcast on append to 'audit' channel

Append-only. No updates. No deletes.
"""
from __future__ import annotations

from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit_log import AuditLog
from models.enums import AuditActorType
from realtime.broadcast import BroadcastService
from realtime.protocol import RealtimeEvent
from repositories.audit_log import AuditLogRepository
from repositories.base import PageResult

logger = structlog.get_logger(__name__)

broadcast_service = BroadcastService()

AUDIT_CHANNEL = "audit"
EVT_AUDIT_APPENDED = "audit.appended"


class AuditTimelineRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = AuditLogRepository(session)

    async def append(
        self,
        action: str,
        target_type: str,
        actor_type: AuditActorType = AuditActorType.system,
        actor_id: UUID | None = None,
        target_id: UUID | None = None,
        correlation_id: UUID | None = None,
        payload: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        """Append an audit event. Broadcasts to 'audit' WS channel."""
        entry = await self._repo.create(
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            correlation_id=correlation_id,
            payload=payload or {},
            ip_address=ip_address,
            user_agent=user_agent,
        )
        logger.info(
            "audit.appended",
            audit_id=str(entry.id),
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
        )
        await broadcast_service.publish(
            RealtimeEvent(
                channel=AUDIT_CHANNEL,
                event_type=EVT_AUDIT_APPENDED,
                payload={
                    "audit_id": str(entry.id),
                    "action": action,
                    "target_type": target_type,
                    "target_id": str(target_id) if target_id else None,
                    "actor_type": actor_type,
                    "actor_id": str(actor_id) if actor_id else None,
                },
            )
        )
        return entry

    async def get_timeline(
        self,
        page: int = 1,
        page_size: int = 50,
        actor_id: UUID | None = None,
        target_type: str | None = None,
        target_id: UUID | None = None,
        action: str | None = None,
    ) -> PageResult[AuditLog]:
        return await self._repo.get_timeline(
            page=page,
            page_size=page_size,
            actor_id=actor_id,
            target_type=target_type,
            target_id=target_id,
            action=action,
        )

    async def get_by_target(
        self, target_type: str, target_id: UUID,
        page: int = 1, page_size: int = 20,
    ) -> PageResult[AuditLog]:
        return await self._repo.get_by_target(target_type, target_id, page=page, page_size=page_size)

    async def get_by_actor(
        self, actor_id: UUID,
        page: int = 1, page_size: int = 20,
    ) -> PageResult[AuditLog]:
        return await self._repo.get_by_actor(actor_id, page=page, page_size=page_size)

    async def get_by_correlation(
        self, correlation_id: UUID,
        page: int = 1, page_size: int = 50,
    ) -> PageResult[AuditLog]:
        return await self._repo.get_by_correlation(correlation_id, page=page, page_size=page_size)
