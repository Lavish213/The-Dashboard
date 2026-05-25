"""
Domain event persistence tests.
Covers: append, seq_num ordering, idempotency, replay cursor, has_more.
"""
from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from events.contracts import DomainEvent
from events.idempotency import DuplicateEventError
from events.replay import replay_channel
from events.store import EventStore


@pytest.fixture
def store() -> EventStore:
    return EventStore()


# ── append ────────────────────────────────────────────────────────────────────

async def test_append_returns_seq_num_1_on_empty_channel(db: AsyncSession, store: EventStore) -> None:
    event = DomainEvent(channel="approvals", event_type="approval.created")
    stored = await store.append(db, event)
    assert stored.seq_num == 1
    assert stored.event_id == event.event_id


async def test_append_increments_seq_num(db: AsyncSession, store: EventStore) -> None:
    ch = "approvals"
    e1 = DomainEvent(channel=ch, event_type="approval.created")
    e2 = DomainEvent(channel=ch, event_type="approval.decided")
    s1 = await store.append(db, e1)
    s2 = await store.append(db, e2)
    assert s1.seq_num == 1
    assert s2.seq_num == 2


async def test_seq_num_scoped_per_channel(db: AsyncSession, store: EventStore) -> None:
    ea = DomainEvent(channel="approvals", event_type="x")
    ew = DomainEvent(channel="system", event_type="x")
    sa_ = await store.append(db, ea)
    sw = await store.append(db, ew)
    assert sa_.seq_num == 1
    assert sw.seq_num == 1  # independent per channel


async def test_duplicate_event_id_raises(db: AsyncSession, store: EventStore) -> None:
    event = DomainEvent(channel="approvals", event_type="approval.created")
    await store.append(db, event)
    with pytest.raises(DuplicateEventError) as exc_info:
        await store.append(db, event)
    assert exc_info.value.event_id == event.event_id


async def test_append_preserves_payload(db: AsyncSession, store: EventStore) -> None:
    payload = {"workflow_id": "abc-123", "requested_by": "user-456"}
    event = DomainEvent(channel="approvals", event_type="approval.created", payload=payload)
    stored = await store.append(db, event)
    assert stored.payload == payload


async def test_append_preserves_correlation_id(db: AsyncSession, store: EventStore) -> None:
    event = DomainEvent(
        channel="system", event_type="system.event", correlation_id="corr-xyz"
    )
    stored = await store.append(db, event)
    assert stored.correlation_id == "corr-xyz"


# ── replay ────────────────────────────────────────────────────────────────────

async def test_replay_empty_channel_returns_empty(db: AsyncSession) -> None:
    events, has_more = await replay_channel(db, "approvals")
    assert events == []
    assert has_more is False


async def test_replay_returns_all_events_ordered(db: AsyncSession, store: EventStore) -> None:
    ch = "approvals"
    for i in range(3):
        await store.append(db, DomainEvent(channel=ch, event_type=f"evt.{i}"))

    events, has_more = await replay_channel(db, ch)
    assert len(events) == 3
    assert [e.seq_num for e in events] == [1, 2, 3]
    assert has_more is False


async def test_replay_from_event_id_cursor(db: AsyncSession, store: EventStore) -> None:
    ch = "approvals"
    stored = []
    for i in range(5):
        s = await store.append(db, DomainEvent(channel=ch, event_type=f"evt.{i}"))
        stored.append(s)

    # Replay after seq 2 (events 3, 4, 5)
    events, has_more = await replay_channel(db, ch, from_event_id=stored[1].event_id)
    assert len(events) == 3
    assert events[0].seq_num == 3
    assert has_more is False


async def test_replay_has_more_when_limit_exceeded(db: AsyncSession, store: EventStore) -> None:
    ch = "system"
    for i in range(5):
        await store.append(db, DomainEvent(channel=ch, event_type=f"evt.{i}"))

    events, has_more = await replay_channel(db, ch, limit=3)
    assert len(events) == 3
    assert has_more is True


async def test_replay_unknown_from_event_id_returns_from_start(
    db: AsyncSession, store: EventStore
) -> None:
    ch = "approvals"
    for i in range(3):
        await store.append(db, DomainEvent(channel=ch, event_type=f"evt.{i}"))

    events, _ = await replay_channel(db, ch, from_event_id="nonexistent-id")
    assert len(events) == 3
    assert events[0].seq_num == 1


async def test_replay_isolated_by_channel(db: AsyncSession, store: EventStore) -> None:
    await store.append(db, DomainEvent(channel="approvals", event_type="x"))
    await store.append(db, DomainEvent(channel="system", event_type="y"))

    approvals, _ = await replay_channel(db, "approvals")
    system, _ = await replay_channel(db, "system")

    assert len(approvals) == 1
    assert len(system) == 1
    assert approvals[0].event_type == "x"
    assert system[0].event_type == "y"
