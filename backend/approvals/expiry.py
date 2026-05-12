"""
ApprovalExpiryRuntime: detects and marks expired pending approvals.

Append-only events. No hidden mutations.
Callers/workers decide scheduling (e.g. a periodic worker).
Replay-safe: expiry is idempotent — re-running on already-expired approvals is a no-op.
"""

from dataclasses import dataclass, field
from uuid import UUID

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import ApprovalStatus, AuditActorType
from realtime.broadcast import broadcast_service
from realtime.protocol import RealtimeEvent
from repositories.approval import ApprovalRepository
from workflows.persistence import WorkflowEventRepository

logger = structlog.get_logger(__name__)

APPROVAL_CHANNEL = "approvals"
EVT_APPROVAL_EXPIRED = "approval.expired"


@dataclass(frozen=True)
class ExpiryResult:
    expired_count: int
    approval_ids: list[UUID] = field(default_factory=list)


class ApprovalExpiryRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = ApprovalRepository(session)
        self._events = WorkflowEventRepository(session)

    async def expire_pending(self) -> ExpiryResult:
        """
        Detect all past-deadline pending approvals.
        Mark each as expired. Emit append-only event per approval.
        Broadcasts realtime event per expiry.
        Returns summary of what was expired.
        """
        candidates = await self._repo.get_expired_pending()
        expired_ids: list[UUID] = []

        for approval in candidates:
            approval.approval_status = ApprovalStatus.expired
            self._session.add(approval)
            await self._session.flush()

            await self._events.append_event(
                workflow_id=approval.workflow_id,
                event_type=EVT_APPROVAL_EXPIRED,
                payload={
                    "approval_id": str(approval.id),
                    "approval_type": approval.approval_type,
                    "expires_at": approval.expires_at.isoformat() if approval.expires_at else None,
                },
                actor_type=AuditActorType.system,
                actor_id=None,
                correlation_id=approval.workflow_id,
            )

            await broadcast_service.publish(RealtimeEvent(
                channel=APPROVAL_CHANNEL,
                event_type=EVT_APPROVAL_EXPIRED,
                payload={
                    "approval_id": str(approval.id),
                    "workflow_id": str(approval.workflow_id),
                    "approval_type": approval.approval_type,
                },
                correlation_id=str(approval.workflow_id),
            ))

            expired_ids.append(approval.id)
            logger.info(
                "approval.expired",
                approval_id=str(approval.id),
                workflow_id=str(approval.workflow_id),
            )

        return ExpiryResult(expired_count=len(expired_ids), approval_ids=expired_ids)
