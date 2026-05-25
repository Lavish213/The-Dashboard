"""
ConnectionManager: in-process registry of active WebSocket connections.

Each connection identified by UUID string (connection_id).
Uses asyncio.Lock for safe concurrent access.
Does NOT hold user state — WS endpoint maps connection_id → user_id.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import WebSocket

logger = structlog.get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> str:
        """Accept WebSocket and register it. Returns connection_id."""
        await ws.accept()
        connection_id = str(uuid.uuid4())
        async with self._lock:
            self._connections[connection_id] = ws
        logger.info(
            "realtime.connection.opened",
            connection_id=connection_id,
            total=len(self._connections),
        )
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Remove a connection. Safe to call if already removed."""
        async with self._lock:
            self._connections.pop(connection_id, None)
        logger.info(
            "realtime.connection.closed",
            connection_id=connection_id,
            total=len(self._connections),
        )

    async def send_json(self, connection_id: str, data: dict[str, Any]) -> bool:
        """
        Send JSON to one connection. Returns True on success.
        Auto-removes stale connections on send failure.
        """
        ws = self._connections.get(connection_id)
        if ws is None:
            return False
        try:
            await ws.send_json(data)
            return True
        except Exception as exc:
            logger.warning(
                "realtime.connection.send_failed",
                connection_id=connection_id,
                error=str(exc),
            )
            await self.disconnect(connection_id)
            return False

    async def close_connection(self, connection_id: str) -> None:
        """Close the underlying WebSocket and remove from registry."""
        async with self._lock:
            ws = self._connections.pop(connection_id, None)
        if ws is not None:
            try:
                await ws.close(code=1001)
            except Exception:
                pass
        logger.info("realtime.connection.evicted", connection_id=connection_id)

    async def broadcast_json(self, connection_ids: set[str], data: dict[str, Any]) -> int:
        """Send JSON to multiple connections concurrently. Returns success count."""
        if not connection_ids:
            return 0
        results = await asyncio.gather(
            *[self.send_json(cid, data) for cid in connection_ids],
            return_exceptions=True,
        )
        return sum(1 for r in results if r is True)

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    def is_connected(self, connection_id: str) -> bool:
        return connection_id in self._connections


# Module-level singleton
connection_manager = ConnectionManager()
