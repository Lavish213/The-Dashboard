import uuid
from uuid import UUID

import structlog

from models.enums import AuditActorType
from observability.correlation import get_correlation_id

logger = structlog.get_logger(__name__)


class AuditService:
    """
    Writes audit log entries to the DB.
    Each important mutation should call log_action().
    Uses its own session from async_session_factory (fire-and-forget safe).
    """

    async def log_action(
        self,
        action: str,
        target_type: str,
        actor_type: AuditActorType = AuditActorType.system,
        actor_id: UUID | None = None,
        target_id: UUID | None = None,
        payload: dict | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """
        Write one audit log entry. Opens its own session so callers
        don't need to pass one in — this keeps audit writes independent
        of the request transaction.

        Swallows exceptions after logging them — audit must never crash the caller.
        """
        from db.session import async_session_factory
        from models.audit_log import AuditLog

        try:
            async with async_session_factory() as session:
                entry = AuditLog(
                    actor_id=actor_id,
                    actor_type=actor_type,
                    action=action,
                    target_type=target_type,
                    target_id=target_id,
                    correlation_id=uuid.UUID(get_correlation_id()) if get_correlation_id() else None,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    payload=payload or {},
                )
                session.add(entry)
                await session.commit()
        except Exception as exc:
            logger.error(
                "audit.write_failed",
                action=action,
                target_type=target_type,
                error=str(exc),
            )


# Module-level singleton — import and use directly
audit = AuditService()
