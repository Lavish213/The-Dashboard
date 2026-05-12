"""
OperatorSessionRuntime — operator WebSocket session lifecycle.

Responsibilities:
- connect operator session (create/update RealtimeSession row)
- disconnect
- heartbeat tracking
- stale session cleanup
- force disconnect (admin action)
- active session query

Append-only audit events via AuditService.
Deterministic transitions. No hidden state.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import RealtimeSessionStatus
from models.realtime_session import RealtimeSession
from repositories.base import BaseRepository, PageResult

logger = structlog.get_logger(__name__)

HEARTBEAT_STALE_SECONDS: int = 90  # 3 missed pings at 30s interval


@dataclass(frozen=True)
class StaleSessionResult:
    expired_count: int
    session_ids: list[UUID]


class RealtimeSessionRepository(BaseRepository[RealtimeSession]):
    def __init__(self, session: AsyncSession):
        super().__init__(session, RealtimeSession)

    async def get_for_update(self, session_id: UUID) -> RealtimeSession | None:
        result = await self.session.execute(
            select(RealtimeSession)
            .where(RealtimeSession.id == session_id)
            .with_for_update()
        )
        return result.scalar_one_or_none()

    async def get_for_update_or_raise(self, session_id: UUID) -> RealtimeSession:
        from core.exceptions import NotFoundError
        obj = await self.get_for_update(session_id)
        if obj is None:
            raise NotFoundError(RealtimeSession.__tablename__, str(session_id))
        return obj

    async def get_active_by_user(self, user_id: UUID) -> list[RealtimeSession]:
        result = await self.session.execute(
            select(RealtimeSession)
            .where(
                RealtimeSession.user_id == user_id,
                RealtimeSession.session_status == RealtimeSessionStatus.connected,
            )
            .order_by(RealtimeSession.connected_at.desc())
        )
        return list(result.scalars().all())

    async def get_all_active(self, page: int = 1, page_size: int = 50) -> PageResult[RealtimeSession]:
        return await self.list_paginated(
            page=page,
            page_size=page_size,
            filters=[RealtimeSession.session_status == RealtimeSessionStatus.connected],
            order_by=RealtimeSession.connected_at.desc(),
        )

    async def get_stale_connected(self, threshold_seconds: int = HEARTBEAT_STALE_SECONDS) -> list[RealtimeSession]:
        """Return connected sessions whose heartbeat has expired."""
        cutoff = datetime.now(UTC) - timedelta(seconds=threshold_seconds)
        result = await self.session.execute(
            select(RealtimeSession).where(
                RealtimeSession.session_status == RealtimeSessionStatus.connected,
                RealtimeSession.last_heartbeat_at.is_not(None),
                RealtimeSession.last_heartbeat_at < cutoff,
            )
        )
        return list(result.scalars().all())

    async def get_by_socket_id(self, socket_id: str) -> RealtimeSession | None:
        result = await self.session.execute(
            select(RealtimeSession).where(
                RealtimeSession.socket_id == socket_id,
                RealtimeSession.session_status == RealtimeSessionStatus.connected,
            )
        )
        return result.scalar_one_or_none()


class OperatorSessionRuntime:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._repo = RealtimeSessionRepository(session)

    async def connect(
        self,
        user_id: UUID,
        socket_id: str,
        device_info: str | None = None,
    ) -> RealtimeSession:
        """Register a new operator session. Called when WS connection established."""
        now = datetime.now(UTC)
        rs = await self._repo.create(
            user_id=user_id,
            socket_id=socket_id,
            session_status=RealtimeSessionStatus.connected,
            connected_at=now,
            last_heartbeat_at=now,
            device_info=device_info,
        )
        logger.info("operator.session.connected", user_id=str(user_id), session_id=str(rs.id))
        return rs

    async def disconnect(self, session_id: UUID) -> RealtimeSession:
        """Mark session as disconnected."""
        rs = await self._repo.get_for_update_or_raise(session_id)
        rs.session_status = RealtimeSessionStatus.disconnected
        rs.disconnected_at = datetime.now(UTC)
        self._session.add(rs)
        await self._session.flush()
        logger.info("operator.session.disconnected", session_id=str(session_id))
        return rs

    async def heartbeat(self, session_id: UUID) -> RealtimeSession:
        """Update last_heartbeat_at for an active session."""
        rs = await self._repo.get_for_update_or_raise(session_id)
        rs.last_heartbeat_at = datetime.now(UTC)
        self._session.add(rs)
        await self._session.flush()
        return rs

    async def force_disconnect(self, user_id: UUID) -> list[UUID]:
        """
        Force-disconnect all active sessions for a user (admin action).
        Returns list of terminated session IDs.
        """
        sessions = await self._repo.get_active_by_user(user_id)
        terminated: list[UUID] = []
        now = datetime.now(UTC)
        for rs in sessions:
            rs.session_status = RealtimeSessionStatus.expired
            rs.disconnected_at = now
            self._session.add(rs)
            terminated.append(rs.id)
        if terminated:
            await self._session.flush()
        logger.info("operator.session.force_disconnect", user_id=str(user_id), count=len(terminated))
        return terminated

    async def cleanup_stale(self, threshold_seconds: int = HEARTBEAT_STALE_SECONDS) -> StaleSessionResult:
        """
        Expire sessions whose heartbeat has lapsed.
        Idempotent: already-expired sessions are not re-processed.
        """
        stale = await self._repo.get_stale_connected(threshold_seconds)
        expired_ids: list[UUID] = []
        now = datetime.now(UTC)
        for rs in stale:
            rs.session_status = RealtimeSessionStatus.expired
            rs.disconnected_at = now
            self._session.add(rs)
            expired_ids.append(rs.id)
        if expired_ids:
            await self._session.flush()
        return StaleSessionResult(expired_count=len(expired_ids), session_ids=expired_ids)

    async def get_active_sessions(self, page: int = 1, page_size: int = 50) -> PageResult[RealtimeSession]:
        return await self._repo.get_all_active(page=page, page_size=page_size)

    async def active_count(self) -> int:
        return await self._repo.count(
            filters=[RealtimeSession.session_status == RealtimeSessionStatus.connected]
        )
