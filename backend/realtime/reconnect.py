"""
Heartbeat and stale connection detection.

HeartbeatTracker records last pong per connection.
Stale threshold: 90s (3 missed pings at 30s interval).
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 30
STALE_THRESHOLD_SECONDS = 90


@dataclass
class HeartbeatTracker:
    _last_pong: dict[str, float] = field(default_factory=dict)

    def record_connect(self, connection_id: str) -> None:
        self._last_pong[connection_id] = time.monotonic()

    def record_pong(self, connection_id: str) -> None:
        self._last_pong[connection_id] = time.monotonic()

    def record_disconnect(self, connection_id: str) -> None:
        self._last_pong.pop(connection_id, None)

    def is_stale(self, connection_id: str) -> bool:
        last = self._last_pong.get(connection_id)
        if last is None:
            return True
        return (time.monotonic() - last) > STALE_THRESHOLD_SECONDS

    def stale_connections(self) -> list[str]:
        now = time.monotonic()
        return [
            cid for cid, last in self._last_pong.items()
            if (now - last) > STALE_THRESHOLD_SECONDS
        ]

    @property
    def tracked_count(self) -> int:
        return len(self._last_pong)


# Module-level singleton
heartbeat_tracker = HeartbeatTracker()
