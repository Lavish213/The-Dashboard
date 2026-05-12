"""
Phase 9 — Notification Runtime Integration Tests.

Covers:
- create appends notification, broadcasts
- mark_read sets read_at
- mark_all_read marks all unread, idempotent
- unread_count accuracy
- paginated feed (all / unread_only)
- read_at idempotency (double mark)
"""

import uuid
from unittest.mock import AsyncMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import NotificationType, UserRole, UserStatus
from models.user import User
from repositories.notification import NotificationRepository
from services.notifications import NotificationRuntime


async def _make_user(db: AsyncSession) -> uuid.UUID:
    user = User(
        email=f"test-{uuid.uuid4()}@example.com",
        hashed_password="x",
        role=UserRole.operator,
        status=UserStatus.active,
    )
    db.add(user)
    await db.flush()
    return user.id


@pytest.fixture(autouse=True)
def _no_broadcast(monkeypatch):
    monkeypatch.setattr(
        "services.notifications.broadcast_service.publish",
        AsyncMock(return_value=0),
    )


def _rt(db: AsyncSession) -> NotificationRuntime:
    return NotificationRuntime(db)


def _repo(db: AsyncSession) -> NotificationRepository:
    return NotificationRepository(db)


async def _make(db: AsyncSession, user_id: uuid.UUID, title: str = "T") -> object:
    return await _rt(db).create(
        user_id=user_id,
        notification_type=NotificationType.system_alert,
        title=title,
        body="body",
    )


# ---------------------------------------------------------------------------
# TestCreate
# ---------------------------------------------------------------------------

class TestCreate:
    async def test_creates_with_correct_fields(self, db: AsyncSession):
        user_id = await _make_user(db)
        notif = await _make(db, user_id, title="Hello")
        assert notif.id is not None
        assert notif.user_id == user_id
        assert notif.title == "Hello"
        assert notif.read_at is None

    async def test_creates_multiple_for_same_user(self, db: AsyncSession):
        user_id = await _make_user(db)
        n1 = await _make(db, user_id, "First")
        n2 = await _make(db, user_id, "Second")
        assert n1.id != n2.id

    async def test_broadcast_called_on_create(self, db: AsyncSession, monkeypatch):
        mock_pub = AsyncMock(return_value=1)
        monkeypatch.setattr("services.notifications.broadcast_service.publish", mock_pub)
        user_id = await _make_user(db)
        await _make(db, user_id)
        mock_pub.assert_awaited_once()


# ---------------------------------------------------------------------------
# TestMarkRead
# ---------------------------------------------------------------------------

class TestMarkRead:
    async def test_sets_read_at(self, db: AsyncSession):
        user_id = await _make_user(db)
        notif = await _make(db, user_id)
        updated = await _rt(db).mark_read(notif.id, user_id)
        assert updated is not None
        assert updated.read_at is not None

    async def test_wrong_user_returns_none(self, db: AsyncSession):
        user_id = await _make_user(db)
        notif = await _make(db, user_id)
        result = await _rt(db).mark_read(notif.id, uuid.uuid4())
        assert result is None

    async def test_missing_notification_returns_none(self, db: AsyncSession):
        result = await _rt(db).mark_read(uuid.uuid4(), uuid.uuid4())
        assert result is None

    async def test_double_mark_read_idempotent(self, db: AsyncSession):
        user_id = await _make_user(db)
        notif = await _make(db, user_id)
        first = await _rt(db).mark_read(notif.id, user_id)
        second = await _rt(db).mark_read(notif.id, user_id)
        assert first.read_at == second.read_at


# ---------------------------------------------------------------------------
# TestMarkAllRead
# ---------------------------------------------------------------------------

class TestMarkAllRead:
    async def test_marks_all_unread(self, db: AsyncSession):
        user_id = await _make_user(db)
        await _make(db, user_id, "A")
        await _make(db, user_id, "B")
        await _make(db, user_id, "C")
        count = await _rt(db).mark_all_read(user_id)
        assert count == 3

    async def test_idempotent_second_call_returns_zero(self, db: AsyncSession):
        user_id = await _make_user(db)
        await _make(db, user_id)
        await _rt(db).mark_all_read(user_id)
        second = await _rt(db).mark_all_read(user_id)
        assert second == 0

    async def test_does_not_affect_other_users(self, db: AsyncSession):
        user_a = await _make_user(db)
        user_b = await _make_user(db)
        await _make(db, user_a)
        await _make(db, user_b)
        await _rt(db).mark_all_read(user_a)
        count_b = await _rt(db).unread_count(user_b)
        assert count_b >= 1

    async def test_no_notifications_returns_zero(self, db: AsyncSession):
        user_id = await _make_user(db)
        result = await _rt(db).mark_all_read(user_id)
        assert result == 0


# ---------------------------------------------------------------------------
# TestUnreadCount
# ---------------------------------------------------------------------------

class TestUnreadCount:
    async def test_counts_unread_only(self, db: AsyncSession):
        user_id = await _make_user(db)
        n1 = await _make(db, user_id)
        await _make(db, user_id)
        await _rt(db).mark_read(n1.id, user_id)
        count = await _rt(db).unread_count(user_id)
        assert count == 1

    async def test_zero_when_all_read(self, db: AsyncSession):
        user_id = await _make_user(db)
        await _make(db, user_id)
        await _rt(db).mark_all_read(user_id)
        count = await _rt(db).unread_count(user_id)
        assert count == 0


# ---------------------------------------------------------------------------
# TestGetFeed
# ---------------------------------------------------------------------------

class TestGetFeed:
    async def test_returns_all_notifications_paginated(self, db: AsyncSession):
        user_id = await _make_user(db)
        for i in range(5):
            await _make(db, user_id, f"N{i}")
        result = await _rt(db).get_feed(user_id, page=1, page_size=3)
        assert len(result.items) == 3
        assert result.total >= 5

    async def test_unread_only_excludes_read(self, db: AsyncSession):
        user_id = await _make_user(db)
        n1 = await _make(db, user_id, "Read")
        await _make(db, user_id, "Unread")
        await _rt(db).mark_read(n1.id, user_id)
        result = await _rt(db).get_feed(user_id, unread_only=True)
        assert all(n.read_at is None for n in result.items)

    async def test_ordered_descending_by_created_at(self, db: AsyncSession):
        user_id = await _make_user(db)
        await _make(db, user_id, "First")
        await _make(db, user_id, "Second")
        result = await _rt(db).get_feed(user_id)
        dates = [n.created_at for n in result.items]
        assert dates == sorted(dates, reverse=True)

    async def test_page_two_returns_next_items(self, db: AsyncSession):
        user_id = await _make_user(db)
        for i in range(6):
            await _make(db, user_id, f"Item{i}")
        p1 = await _rt(db).get_feed(user_id, page=1, page_size=4)
        p2 = await _rt(db).get_feed(user_id, page=2, page_size=4)
        ids_p1 = {n.id for n in p1.items}
        ids_p2 = {n.id for n in p2.items}
        assert ids_p1.isdisjoint(ids_p2)
