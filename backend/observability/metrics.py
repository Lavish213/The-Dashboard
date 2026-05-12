"""
Runtime metrics — in-process counters for operational health.

Lightweight, no external dependency. Prometheus-exportable if needed later.
Thread-safe via simple integer increments (GIL-safe for CPython).
Reset is not supported — counters are monotonic.

Live gauge values (connections, stale) are read from singletons at snapshot time.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class RuntimeMetrics:
    # Request counters
    requests_total: int = 0
    requests_5xx: int = 0
    requests_4xx: int = 0

    # WebSocket lifecycle (monotonic)
    ws_connections_total: int = 0

    # Operator sessions
    operator_sessions_connected: int = 0
    operator_sessions_expired: int = 0

    # Notifications
    notifications_created: int = 0

    # Audit
    audit_events_appended: int = 0

    # Call sessions
    call_sessions_created: int = 0
    call_sessions_completed: int = 0
    call_sessions_failed: int = 0

    # Uptime
    started_at: float = field(default_factory=time.monotonic)

    def uptime_seconds(self) -> float:
        return time.monotonic() - self.started_at

    def snapshot(self) -> dict:
        # Import live singletons here to avoid circular imports at module load
        from realtime.manager import connection_manager
        from realtime.reconnect import heartbeat_tracker

        return {
            "uptime_seconds": round(self.uptime_seconds(), 2),
            "requests": {
                "total": self.requests_total,
                "5xx": self.requests_5xx,
                "4xx": self.requests_4xx,
            },
            "websocket": {
                "active_connections": connection_manager.connection_count,
                "stale_connections": len(heartbeat_tracker.stale_connections()),
            },
            "operator_sessions": {
                "connected_total": self.operator_sessions_connected,
                "expired_total": self.operator_sessions_expired,
            },
            "notifications": {
                "created_total": self.notifications_created,
            },
            "audit": {
                "events_total": self.audit_events_appended,
            },
            "call_sessions": {
                "created_total": self.call_sessions_created,
                "completed_total": self.call_sessions_completed,
                "failed_total": self.call_sessions_failed,
            },
        }


# Process-global singleton
metrics = RuntimeMetrics()
