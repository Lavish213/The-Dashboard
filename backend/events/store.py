"""
EventStore — append-only event persistence with deterministic channel-scoped seq_num.

seq_num assignment:
  A PostgreSQL advisory transaction lock (pg_advisory_xact_lock) is acquired
  per channel before reading MAX(seq_num). This serializes concurrent writers
  on the same channel without a separate sequence table.

  Lock key: lower 63 bits of MD5(channel) — stable, positive, fits bigint.

Idempotency:
  event_id has a unique constraint. IntegrityError on duplicate is re-raised
  as DuplicateEventError. Caller is responsible for session rollback.
"""
from __future__ import annotations

import hashlib

import structlog
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent, StoredEvent
from events.idempotency import DuplicateEventError
from models.domain_event import DomainEventModel

logger = structlog.get_logger(__name__)


def _channel_lock_id(channel: str) -> int:
    """Stable 63-bit lock key from channel name. Always positive, fits bigint."""
    return int(hashlib.md5(channel.encode()).hexdigest()[:15], 16)


class EventStore:
    async def append(self, session: AsyncSession, event: DomainEvent) -> StoredEvent:
        """
        Persist event and return StoredEvent with assigned seq_num.
        Raises DuplicateEventError if event_id already exists.
        Does NOT commit — caller owns the transaction.
        """
        # Serialize writers per channel for this transaction
        await session.execute(
            text("SELECT pg_advisory_xact_lock(:h)"),
            {"h": _channel_lock_id(event.channel)},
        )

        result = await session.execute(
            text(
                "SELECT COALESCE(MAX(seq_num), 0) + 1 "
                "FROM domain_events WHERE channel = :c"
            ),
            {"c": event.channel},
        )
        seq_num: int = result.scalar_one()

        row = DomainEventModel(
            event_id=event.event_id,
            channel=event.channel,
            seq_num=seq_num,
            event_type=event.event_type,
            payload=event.payload,
            correlation_id=event.correlation_id,
            occurred_at=event.occurred_at,
        )
        session.add(row)

        try:
            await session.flush()
        except IntegrityError as exc:
            raise DuplicateEventError(event.event_id) from exc

        logger.info(
            "events.store.appended",
            event_id=event.event_id,
            channel=event.channel,
            seq_num=seq_num,
            event_type=event.event_type,
        )
        return StoredEvent(seq_num=seq_num, **event.model_dump())

    async def fetch_after(
        self,
        session: AsyncSession,
        channel: str,
        from_event_id: str | None,
        limit: int,
    ) -> tuple[list[StoredEvent], bool]:
        """
        Return events on `channel` with seq_num > cursor, ordered ascending.
        Cursor is resolved from `from_event_id` (seq_num of that event).
        Returns (events, has_more).
        """
        start_seq = 0
        if from_event_id:
            r = await session.execute(
                text(
                    "SELECT seq_num FROM domain_events "
                    "WHERE channel = :c AND event_id = :e"
                ),
                {"c": channel, "e": from_event_id},
            )
            val = r.scalar_one_or_none()
            if val is not None:
                start_seq = val

        r = await session.execute(
            text(
                "SELECT event_id, channel, seq_num, event_type, payload, "
                "correlation_id, occurred_at "
                "FROM domain_events "
                "WHERE channel = :c AND seq_num > :s "
                "ORDER BY seq_num ASC LIMIT :lim"
            ),
            {"c": channel, "s": start_seq, "lim": limit + 1},
        )
        rows = r.fetchall()
        has_more = len(rows) > limit
        rows = rows[:limit]

        return (
            [
                StoredEvent(
                    event_id=row.event_id,
                    channel=row.channel,
                    seq_num=row.seq_num,
                    event_type=row.event_type,
                    payload=row.payload or {},
                    correlation_id=row.correlation_id,
                    occurred_at=row.occurred_at,
                )
                for row in rows
            ],
            has_more,
        )


# Module-level singleton
event_store = EventStore()
