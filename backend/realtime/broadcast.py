"""
BroadcastService: sends RealtimeEvents to all subscribers of a channel.
Composes ConnectionManager + SubscriptionManager.
"""
from __future__ import annotations

import structlog

from realtime.manager import connection_manager
from realtime.protocol import RealtimeEvent
from realtime.subscriptions import subscription_manager

logger = structlog.get_logger(__name__)


class BroadcastService:
    async def publish(self, event: RealtimeEvent) -> int:
        """
        Broadcast a RealtimeEvent to all subscribers of event.channel.
        Returns number of connections that received the event.
        """
        subscribers = subscription_manager.subscribers(event.channel)
        if not subscribers:
            return 0

        payload = event.model_dump()
        sent = await connection_manager.broadcast_json(subscribers, payload)

        logger.info(
            "realtime.broadcast.published",
            channel=event.channel,
            event_type=event.event_type,
            event_id=event.event_id,
            subscribers=len(subscribers),
            sent=sent,
        )
        return sent

    async def publish_to_connection(self, connection_id: str, event: RealtimeEvent) -> bool:
        """Send a single event directly to one connection (e.g. for replay)."""
        return await connection_manager.send_json(connection_id, event.model_dump())


# Module-level singleton
broadcast_service = BroadcastService()
