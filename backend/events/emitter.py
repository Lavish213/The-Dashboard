"""
EventEmitter — persist a DomainEvent and return StoredEvent.

Two emission modes:
  emit()             — persist only. Caller commits and broadcasts.
                       Use for internal events that don't need cross-process fanout.

  emit_and_publish() — persist + Redis PUBLISH after commit.
                       Use for sophia handoff, mode change, and any event
                       the dashboard must receive in realtime across processes.

Broadcast is intentionally separated from persistence.
Events are only visible after commit — correct ordering guaranteed.
"""
from __future__ import annotations

import json

from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from events.contracts import DomainEvent, StoredEvent
from events.store import event_store


class EventEmitter:
    async def emit(
        self,
        session: AsyncSession,
        event: DomainEvent,
    ) -> StoredEvent:
        """Persist event. Caller commits and broadcasts."""
        return await event_store.append(session, event)

    async def emit_and_publish(
        self,
        session: AsyncSession,
        event: DomainEvent,
        channel: str | None = None,
    ) -> StoredEvent:
        """
        Persist event, commit, then PUBLISH to Redis.

        Channel defaults to karpathys:sophia:{aggregate_id} if not provided.
        The Redis bridge subscriber picks this up and fans out to all
        connected ws clients subscribed to the channel.

        Call pattern:
          stored = await event_emitter.emit_and_publish(db, event)
          await db.commit()   ← must commit BEFORE publish is meaningful
                               but publish happens after append so ordering holds
        """
        stored = await event_store.append(session, event)

        if channel is None:
            aggregate_id = getattr(event, "aggregate_id", None) or getattr(event, "session_id", None)
            channel = f"karpathys:sophia:{aggregate_id}" if aggregate_id else "karpathys:system"

        try:
            redis = await get_redis().__anext__()
            payload = json.dumps({
                "event_id": str(stored.event_id),
                "event_type": stored.event_type,
                "aggregate_id": str(stored.aggregate_id) if stored.aggregate_id else None,
                "channel": channel,
                "payload": stored.payload,
                "occurred_at": stored.occurred_at.isoformat(),
            })
            await redis.publish(channel, payload)
        except Exception:
            pass

        return stored


event_emitter = EventEmitter()