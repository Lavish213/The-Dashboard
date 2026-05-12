"""
SubscriptionManager: maps channels to subscriber connection IDs.

Channel naming:
  workflow:{uuid}   — per-workflow events
  lead:{uuid}       — per-lead events
  approvals         — all approval events (admin/reviewer)
  system            — system-wide events (admin only)
  user:{uuid}       — user-specific notifications

Permission rules enforced at subscribe time.
This manager is purely in-memory — no DB access.
"""
from __future__ import annotations

import re

import structlog

logger = structlog.get_logger(__name__)

_UUID_RE = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"

_CHANNEL_PATTERNS = [
    re.compile(rf"^workflow:{_UUID_RE}$"),
    re.compile(rf"^lead:{_UUID_RE}$"),
    re.compile(rf"^transcript:{_UUID_RE}$"),
    re.compile(r"^approvals$"),
    re.compile(r"^system$"),
    re.compile(rf"^user:{_UUID_RE}$"),
]

_RESTRICTED_CHANNELS: dict[str, set[str]] = {
    "approvals": {"admin", "reviewer"},
    "system": {"admin"},
}


def validate_channel(channel: str) -> bool:
    """Return True if channel name matches a known pattern."""
    return any(p.match(channel) for p in _CHANNEL_PATTERNS)


def channel_allowed(channel: str, role: str) -> bool:
    """Check if a role may subscribe to a channel."""
    if not validate_channel(channel):
        return False
    base = channel.split(":")[0]
    if base in _RESTRICTED_CHANNELS:
        return role in _RESTRICTED_CHANNELS[base]
    return True


class SubscriptionManager:
    def __init__(self) -> None:
        self._channel_subs: dict[str, set[str]] = {}  # channel → connection_ids
        self._conn_channels: dict[str, set[str]] = {}  # connection_id → channels

    def subscribe(self, connection_id: str, channel: str) -> None:
        """Add a subscription. Idempotent."""
        self._channel_subs.setdefault(channel, set()).add(connection_id)
        self._conn_channels.setdefault(connection_id, set()).add(channel)
        logger.info("realtime.subscription.added", connection_id=connection_id, channel=channel)

    def unsubscribe(self, connection_id: str, channel: str) -> None:
        """Remove one subscription. Safe if not subscribed."""
        self._channel_subs.get(channel, set()).discard(connection_id)
        self._conn_channels.get(connection_id, set()).discard(channel)

    def unsubscribe_all(self, connection_id: str) -> None:
        """Remove all subscriptions for a connection (on disconnect)."""
        channels = self._conn_channels.pop(connection_id, set())
        for ch in channels:
            self._channel_subs.get(ch, set()).discard(connection_id)
        if channels:
            logger.info(
                "realtime.subscription.cleared",
                connection_id=connection_id,
                channel_count=len(channels),
            )

    def subscribers(self, channel: str) -> set[str]:
        """Return copy of connection_ids subscribed to a channel."""
        return set(self._channel_subs.get(channel, set()))

    def channels(self, connection_id: str) -> set[str]:
        """Return copy of channels a connection is subscribed to."""
        return set(self._conn_channels.get(connection_id, set()))

    @property
    def subscription_count(self) -> int:
        return sum(len(v) for v in self._conn_channels.values())

    @property
    def channel_count(self) -> int:
        return len(self._channel_subs)


# Module-level singleton
subscription_manager = SubscriptionManager()
