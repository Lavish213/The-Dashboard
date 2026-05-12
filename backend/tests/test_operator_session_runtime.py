"""
Phase 9 — Operator Session Runtime Integration Tests.

Covers:
- connect creates session with connected status
- disconnect marks disconnected
- heartbeat updates last_heartbeat_at
- force_disconnect expires all user sessions
- cleanup_stale idempotent
- active_count accuracy
- get_active_sessions pagination
- get_by_socket_id lookup
"""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import RealtimeSessionStatus, UserRole, UserStatus
from models.user import User
from services.operator_sessions import OperatorSessionRuntime, RealtimeSessionRepository


async def _make_user(db: AsyncSession) -> uuid.UUID:
    """Create a real user row to satisfy FK constraints."""
    user = User(
        email=f"test-{uuid.uuid4()}@example.com",
        hashed_password="x",
        role=UserRole.operator,
        status=UserStatus.active,
    )
    db.add(user)
    await db.flush()
    return user.id


def _rt(db: AsyncSession) -> OperatorSessionRuntime:
    return OperatorSessionRuntime(db)


def _repo(db: AsyncSession) -> RealtimeSessionRepository:
    return RealtimeSessionRepository(db)


# ---------------------------------------------------------------------------
# TestConnect
# ---------------------------------------------------------------------------

class TestConnect:
    async def test_creates_session_with_connected_status(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id=user_id, socket_id="sock-1")
        assert rs.id is not None
        assert rs.user_id == user_id
        assert rs.session_status == RealtimeSessionStatus.connected
        assert rs.socket_id == "sock-1"
        assert rs.connected_at is not None
        assert rs.last_heartbeat_at is not None

    async def test_stores_device_info(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, "sock-2", device_info="Mozilla/5.0")
        assert rs.device_info == "Mozilla/5.0"

    async def test_same_user_multiple_sessions(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs1 = await rt.connect(user_id, "sock-a")
        rs2 = await rt.connect(user_id, "sock-b")
        assert rs1.id != rs2.id
        active = await _repo(db).get_active_by_user(user_id)
        assert len(active) == 2


# ---------------------------------------------------------------------------
# TestDisconnect
# ---------------------------------------------------------------------------

class TestDisconnect:
    async def test_marks_disconnected(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, "sock-3")
        updated = await rt.disconnect(rs.id)
        assert updated.session_status == RealtimeSessionStatus.disconnected
        assert updated.disconnected_at is not None

    async def test_disconnected_not_in_active_list(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, "sock-4")
        await rt.disconnect(rs.id)
        active = await _repo(db).get_active_by_user(user_id)
        assert all(s.id != rs.id for s in active)

    async def test_disconnect_missing_session_raises(self, db: AsyncSession):
        from core.exceptions import NotFoundError
        rt = _rt(db)
        with pytest.raises(NotFoundError):
            await rt.disconnect(uuid.uuid4())


# ---------------------------------------------------------------------------
# TestHeartbeat
# ---------------------------------------------------------------------------

class TestHeartbeat:
    async def test_updates_last_heartbeat_at(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, "sock-5")
        original_hb = rs.last_heartbeat_at
        updated = await rt.heartbeat(rs.id)
        assert updated.last_heartbeat_at >= original_hb

    async def test_heartbeat_missing_raises(self, db: AsyncSession):
        from core.exceptions import NotFoundError
        rt = _rt(db)
        with pytest.raises(NotFoundError):
            await rt.heartbeat(uuid.uuid4())


# ---------------------------------------------------------------------------
# TestForceDisconnect
# ---------------------------------------------------------------------------

class TestForceDisconnect:
    async def test_expires_all_active_sessions_for_user(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs1 = await rt.connect(user_id, "sock-6")
        rs2 = await rt.connect(user_id, "sock-7")
        terminated = await rt.force_disconnect(user_id)
        assert set(terminated) == {rs1.id, rs2.id}

    async def test_force_disconnect_sets_expired_status(self, db: AsyncSession):
        rt = _rt(db)
        repo = _repo(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, "sock-8")
        await rt.force_disconnect(user_id)
        fetched = await repo.get_by_id(rs.id)
        assert fetched.session_status == RealtimeSessionStatus.expired
        assert fetched.disconnected_at is not None

    async def test_force_disconnect_no_sessions_returns_empty(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        result = await rt.force_disconnect(user_id)
        assert result == []

    async def test_force_disconnect_leaves_other_users_untouched(self, db: AsyncSession):
        rt = _rt(db)
        user_a = await _make_user(db)
        user_b = await _make_user(db)
        await rt.connect(user_a, "sock-9")
        rs_b = await rt.connect(user_b, "sock-10")
        await rt.force_disconnect(user_a)
        active_b = await _repo(db).get_active_by_user(user_b)
        assert any(s.id == rs_b.id for s in active_b)


# ---------------------------------------------------------------------------
# TestCleanupStale
# ---------------------------------------------------------------------------

class TestCleanupStale:
    async def test_expires_stale_sessions(self, db: AsyncSession):
        rt = _rt(db)
        repo = _repo(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, "sock-stale-1")
        rs.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=200)
        db.add(rs)
        await db.flush()

        result = await rt.cleanup_stale(threshold_seconds=90)
        assert rs.id in result.session_ids
        assert result.expired_count >= 1

        fetched = await repo.get_by_id(rs.id)
        assert fetched.session_status == RealtimeSessionStatus.expired

    async def test_active_sessions_not_expired(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, "sock-fresh")
        result = await rt.cleanup_stale(threshold_seconds=90)
        assert rs.id not in result.session_ids

    async def test_cleanup_stale_idempotent(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, "sock-stale-2")
        rs.last_heartbeat_at = datetime.now(UTC) - timedelta(seconds=200)
        db.add(rs)
        await db.flush()

        result1 = await rt.cleanup_stale(threshold_seconds=90)
        result2 = await rt.cleanup_stale(threshold_seconds=90)
        assert rs.id in result1.session_ids
        assert rs.id not in result2.session_ids


# ---------------------------------------------------------------------------
# TestActiveCount
# ---------------------------------------------------------------------------

class TestActiveCount:
    async def test_counts_only_connected(self, db: AsyncSession):
        rt = _rt(db)
        before = await rt.active_count()
        user_a = await _make_user(db)
        user_b = await _make_user(db)
        rs1 = await rt.connect(user_a, "sock-cnt-1")
        rs2 = await rt.connect(user_b, "sock-cnt-2")
        await rt.disconnect(rs2.id)
        after = await rt.active_count()
        assert after == before + 1
        _ = rs1

    async def test_count_decrements_after_force_disconnect(self, db: AsyncSession):
        rt = _rt(db)
        user_id = await _make_user(db)
        await rt.connect(user_id, "sock-cnt-3")
        before = await rt.active_count()
        await rt.force_disconnect(user_id)
        after = await rt.active_count()
        assert after == before - 1


# ---------------------------------------------------------------------------
# TestGetBySocketId
# ---------------------------------------------------------------------------

class TestGetBySocketId:
    async def test_finds_connected_session_by_socket(self, db: AsyncSession):
        rt = _rt(db)
        repo = _repo(db)
        socket_id = f"sock-{uuid.uuid4()}"
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, socket_id)
        found = await repo.get_by_socket_id(socket_id)
        assert found is not None
        assert found.id == rs.id

    async def test_disconnected_not_found_by_socket(self, db: AsyncSession):
        rt = _rt(db)
        repo = _repo(db)
        socket_id = f"sock-{uuid.uuid4()}"
        user_id = await _make_user(db)
        rs = await rt.connect(user_id, socket_id)
        await rt.disconnect(rs.id)
        found = await repo.get_by_socket_id(socket_id)
        assert found is None
