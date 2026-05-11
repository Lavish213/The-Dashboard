"""
Realtime unit tests — pure logic, no live WebSocket connections.
Tests protocol parsing, subscription management, heartbeat, and broadcast.
"""
from __future__ import annotations

import time
import uuid

import pytest

from realtime.protocol import (
    ConnectedAck,
    RealtimeError,
    RealtimeEvent,
    ReplayRequest,
    ReplayResponse,
    SubscribeRequest,
    UnsubscribeRequest,
    parse_client_message,
)
from realtime.reconnect import STALE_THRESHOLD_SECONDS, HeartbeatTracker
from realtime.subscriptions import (
    SubscriptionManager,
    channel_allowed,
    validate_channel,
)

# ── Protocol ──────────────────────────────────────────────────────────────────

class TestProtocol:
    def test_parse_subscribe(self):
        msg = parse_client_message({"type": "subscribe", "channel": "approvals"})
        assert isinstance(msg, SubscribeRequest)
        assert msg.channel == "approvals"

    def test_parse_subscribe_with_last_event_id(self):
        msg = parse_client_message({
            "type": "subscribe",
            "channel": "approvals",
            "last_event_id": "abc-123",
        })
        assert isinstance(msg, SubscribeRequest)
        assert msg.last_event_id == "abc-123"

    def test_parse_unsubscribe(self):
        msg = parse_client_message({"type": "unsubscribe", "channel": "system"})
        assert isinstance(msg, UnsubscribeRequest)

    def test_parse_replay(self):
        msg = parse_client_message({
            "type": "replay",
            "channel": "approvals",
            "from_event_id": "evt-1",
            "limit": 25,
        })
        assert isinstance(msg, ReplayRequest)
        assert msg.limit == 25

    def test_parse_unknown_returns_none(self):
        assert parse_client_message({"type": "unknown"}) is None
        assert parse_client_message({}) is None

    def test_parse_malformed_returns_none(self):
        # limit out of range — parse_client_message swallows ValidationError
        assert parse_client_message({"type": "replay", "channel": "x", "limit": 0}) is None

    def test_realtime_event_has_event_id(self):
        e = RealtimeEvent(channel="approvals", event_type="approval.created")
        assert e.event_id is not None
        assert e.type == "event"
        assert e.occurred_at is not None

    def test_realtime_error_serialises(self):
        err = RealtimeError(code="permission_denied", message="Not allowed", channel="system")
        d = err.model_dump()
        assert d["type"] == "error"
        assert d["code"] == "permission_denied"
        assert d["channel"] == "system"

    def test_connected_ack_defaults(self):
        ack = ConnectedAck(connection_id="conn-abc")
        assert ack.type == "connected"
        assert ack.server_time is not None
        assert ack.user_id is None

    def test_replay_response_empty(self):
        r = ReplayResponse(channel="approvals")
        assert r.events == []
        assert r.has_more is False

    def test_replay_request_limit_bounds(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            ReplayRequest(channel="approvals", limit=0)
        with pytest.raises(ValidationError):
            ReplayRequest(channel="approvals", limit=201)


# ── Channel permissions ───────────────────────────────────────────────────────

class TestChannelPermissions:
    def test_valid_channels(self):
        assert validate_channel(f"workflow:{uuid.uuid4()}")
        assert validate_channel(f"lead:{uuid.uuid4()}")
        assert validate_channel("approvals")
        assert validate_channel("system")
        assert validate_channel(f"user:{uuid.uuid4()}")

    def test_invalid_channels(self):
        assert not validate_channel("random")
        assert not validate_channel("workflow:not-a-uuid")
        assert not validate_channel("lead:")
        assert not validate_channel("")
        assert not validate_channel("APPROVALS")

    def test_approvals_requires_admin_or_reviewer(self):
        assert channel_allowed("approvals", "admin")
        assert channel_allowed("approvals", "reviewer")
        assert not channel_allowed("approvals", "operator")

    def test_system_requires_admin(self):
        assert channel_allowed("system", "admin")
        assert not channel_allowed("system", "reviewer")
        assert not channel_allowed("system", "operator")

    def test_workflow_open_to_all(self):
        ch = f"workflow:{uuid.uuid4()}"
        assert channel_allowed(ch, "operator")
        assert channel_allowed(ch, "reviewer")
        assert channel_allowed(ch, "admin")

    def test_invalid_channel_always_denied(self):
        assert not channel_allowed("hacker_channel", "admin")


# ── SubscriptionManager ───────────────────────────────────────────────────────

class TestSubscriptionManager:
    def test_subscribe_and_subscribers(self):
        sm = SubscriptionManager()
        sm.subscribe("c1", "approvals")
        assert "c1" in sm.subscribers("approvals")
        assert sm.subscription_count == 1

    def test_subscribe_idempotent(self):
        sm = SubscriptionManager()
        sm.subscribe("c1", "approvals")
        sm.subscribe("c1", "approvals")
        assert sm.subscription_count == 1

    def test_multiple_subscribers(self):
        sm = SubscriptionManager()
        sm.subscribe("c1", "approvals")
        sm.subscribe("c2", "approvals")
        sm.subscribe("c3", "approvals")
        assert len(sm.subscribers("approvals")) == 3

    def test_unsubscribe(self):
        sm = SubscriptionManager()
        sm.subscribe("c1", "approvals")
        sm.unsubscribe("c1", "approvals")
        assert "c1" not in sm.subscribers("approvals")
        assert sm.subscription_count == 0

    def test_unsubscribe_all(self):
        sm = SubscriptionManager()
        sm.subscribe("c1", "approvals")
        sm.subscribe("c1", "system")
        sm.subscribe("c2", "approvals")
        sm.unsubscribe_all("c1")
        assert sm.subscription_count == 1
        assert "c1" not in sm.subscribers("approvals")
        assert "c2" in sm.subscribers("approvals")

    def test_channels_for_connection(self):
        sm = SubscriptionManager()
        sm.subscribe("c1", "approvals")
        sm.subscribe("c1", "system")
        assert sm.channels("c1") == {"approvals", "system"}

    def test_subscribers_returns_copy(self):
        sm = SubscriptionManager()
        sm.subscribe("c1", "approvals")
        subs = sm.subscribers("approvals")
        subs.add("injected")
        assert "injected" not in sm.subscribers("approvals")


# ── HeartbeatTracker ──────────────────────────────────────────────────────────

class TestHeartbeatTracker:
    def test_fresh_not_stale(self):
        t = HeartbeatTracker()
        t.record_connect("c1")
        assert not t.is_stale("c1")

    def test_unknown_is_stale(self):
        t = HeartbeatTracker()
        assert t.is_stale("never-seen")

    def test_stale_after_threshold(self):
        t = HeartbeatTracker()
        t.record_connect("c1")
        t._last_pong["c1"] = time.monotonic() - (STALE_THRESHOLD_SECONDS + 1)
        assert t.is_stale("c1")
        assert "c1" in t.stale_connections()

    def test_pong_resets_stale(self):
        t = HeartbeatTracker()
        t.record_connect("c1")
        t._last_pong["c1"] = time.monotonic() - (STALE_THRESHOLD_SECONDS + 1)
        t.record_pong("c1")
        assert not t.is_stale("c1")

    def test_disconnect_removes(self):
        t = HeartbeatTracker()
        t.record_connect("c1")
        t.record_disconnect("c1")
        assert t.tracked_count == 0
