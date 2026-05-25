"""
replay_channel — fetch stored events for a channel starting after from_event_id.
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import StoredEvent
from events.store import event_store


async def replay_channel(
    session: AsyncSession,
    channel: str,
    from_event_id: str | None = None,
    limit: int = 50,
) -> tuple[list[StoredEvent], bool]:
    """
    Return (events, has_more) for `channel`.
    Events are ordered by seq_num ascending.
    If `from_event_id` is given, returns events after that event's seq_num.
    """
    return await event_store.fetch_after(session, channel, from_event_id, limit)
