# Phase 4 — Realtime Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the complete realtime runtime — WebSocket server, connection/subscription management, event broadcast, reconnect/replay, and matching frontend client with stores, hooks, and status components.

**Architecture:** Backend uses a FastAPI WebSocket endpoint with an in-process ConnectionManager (dict of connection_id → WebSocket) and SubscriptionManager (channel → subscriber set). Frontend uses a native browser WebSocket wrapped in a typed client class, with Zustand for connection state and TanStack Query invalidation for cache reconciliation on incoming events. JWT is passed as a query parameter on WS connect.

**Tech Stack:** FastAPI WebSockets (asyncio), Pydantic v2 protocol models, Zustand, TanStack Query, native browser WebSocket, TypeScript strict mode, Next.js App Router providers.

---

## File Map

### Backend (create or fill — all currently empty stubs)

| File | Responsibility |
|------|---------------|
| `backend/realtime/protocol.py` | All Pydantic message models (server→client and client→server) |
| `backend/realtime/manager.py` | ConnectionManager: tracks WS connections by connection_id |
| `backend/realtime/subscriptions.py` | SubscriptionManager: channel→connections mapping |
| `backend/realtime/broadcast.py` | BroadcastService: sends to all channel subscribers |
| `backend/realtime/reconnect.py` | Heartbeat tracker, stale connection detection |
| `backend/api/routes/realtime.py` | WS endpoint + GET /realtime/stats + GET /realtime/health |
| `backend/api/v1/router.py` | Add realtime router |
| `backend/schemas/event.py` | Add RealtimeEventEnvelope schema |
| `backend/tests/test_realtime.py` | Unit tests (no live WS needed — pure logic) |

### Frontend (create or fill — all currently empty or shells)

| File | Responsibility |
|------|---------------|
| `frontend/types/websocket.ts` | All TypeScript WS message type unions |
| `frontend/types/event.ts` | TypeScript realtime event envelope types |
| `frontend/lib/websocket/client.ts` | WebSocketClient class: connect, send, event callbacks |
| `frontend/lib/websocket/reconnect.ts` | Exponential backoff reconnect strategy |
| `frontend/lib/realtime/dispatcher.ts` | Routes incoming server messages to handlers |
| `frontend/lib/realtime/deduplication.ts` | Bounded Set dedup of seen event IDs |
| `frontend/lib/realtime/registry.ts` | Subscription registry: channel→handler map |
| `frontend/stores/websocket.store.ts` | Replace shell: Zustand WS connection state |
| `frontend/stores/realtime.store.ts` | Replace shell: Zustand realtime event state |
| `frontend/providers/WebsocketProvider.tsx` | Replace shell: WS lifecycle, connect/disconnect |
| `frontend/providers/RealtimeProvider.tsx` | Replace shell: event dispatch, query invalidation |
| `frontend/hooks/useWebsocket.ts` | Replace shell: access WS state + send |
| `frontend/hooks/useRealtime.ts` | Replace shell: subscribe to channel, get events |
| `frontend/components/realtime/RealtimeConnectionBadge.tsx` | Inline status dot (idle/connecting/connected/error) |
| `frontend/components/realtime/RealtimeStatus.tsx` | Full status panel with stats |
| `frontend/components/realtime/RealtimeEventFeed.tsx` | Scrolling list of recent events |
| `frontend/app/realtime/page.tsx` | Realtime monitor page using the components above |

---

## Task 1: Backend Protocol Types

**Files:**
- Fill: `backend/realtime/protocol.py`
- Fill (extend): `backend/schemas/event.py`

- [ ] **Step 1: Write the implementation**

```python
# backend/realtime/protocol.py
"""
Wire protocol message types for the Karpathys realtime WebSocket.

Server → Client message types:
  connected    — initial ack after auth
  ping         — heartbeat from server
  event        — domain event broadcast
  subscribed   — subscription confirmation
  unsubscribed — unsubscription confirmation
  replay       — replay response
  error        — error envelope

Client → Server message types:
  pong         — heartbeat response
  subscribe    — subscribe to a channel
  unsubscribe  — unsubscribe from a channel
  replay       — request missed events
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


# ── Server → Client ──────────────────────────────────────────────────────────

class ConnectedAck(BaseModel):
    type: Literal["connected"] = "connected"
    connection_id: str
    server_time: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    user_id: str | None = None


class PingMessage(BaseModel):
    type: Literal["ping"] = "ping"
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class RealtimeEvent(BaseModel):
    """A domain event pushed to subscribed clients."""
    type: Literal["event"] = "event"
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    channel: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    occurred_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SubscribedAck(BaseModel):
    type: Literal["subscribed"] = "subscribed"
    channel: str
    last_event_id: str | None = None


class UnsubscribedAck(BaseModel):
    type: Literal["unsubscribed"] = "unsubscribed"
    channel: str


class ReplayResponse(BaseModel):
    type: Literal["replay"] = "replay"
    channel: str
    events: list[RealtimeEvent] = Field(default_factory=list)
    has_more: bool = False


class RealtimeError(BaseModel):
    type: Literal["error"] = "error"
    code: str
    message: str
    channel: str | None = None


# Union of all server → client messages (used for serialisation only)
ServerMessage = (
    ConnectedAck
    | PingMessage
    | RealtimeEvent
    | SubscribedAck
    | UnsubscribedAck
    | ReplayResponse
    | RealtimeError
)


# ── Client → Server ──────────────────────────────────────────────────────────

class PongMessage(BaseModel):
    type: Literal["pong"] = "pong"
    timestamp: str


class SubscribeRequest(BaseModel):
    type: Literal["subscribe"] = "subscribe"
    channel: str
    last_event_id: str | None = None  # for gap-fill on reconnect


class UnsubscribeRequest(BaseModel):
    type: Literal["unsubscribe"] = "unsubscribe"
    channel: str


class ReplayRequest(BaseModel):
    type: Literal["replay"] = "replay"
    channel: str
    from_event_id: str | None = None
    limit: int = Field(default=50, ge=1, le=200)


def parse_client_message(
    data: dict[str, Any],
) -> PongMessage | SubscribeRequest | UnsubscribeRequest | ReplayRequest | None:
    """Parse a raw dict into a typed client message. Returns None if unknown type."""
    msg_type = data.get("type")
    match msg_type:
        case "pong":
            return PongMessage(**data)
        case "subscribe":
            return SubscribeRequest(**data)
        case "unsubscribe":
            return UnsubscribeRequest(**data)
        case "replay":
            return ReplayRequest(**data)
        case _:
            return None
```

- [ ] **Step 2: Extend `backend/schemas/event.py`**

Append to the existing file (which already has WorkflowEventResponse and AuditLogResponse):

```python
# Add to backend/schemas/event.py — append at end
from realtime.protocol import RealtimeEvent  # re-export for API use

class RealtimeEventEnvelope(BaseModel):
    """HTTP response envelope for replayed events."""
    model_config = ConfigDict(from_attributes=True)
    event_id: str
    channel: str
    event_type: str
    payload: dict
    correlation_id: str | None
    occurred_at: datetime
```

- [ ] **Step 3: Validate imports**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/python -c "
from realtime.protocol import (
    ConnectedAck, PingMessage, RealtimeEvent, SubscribedAck,
    UnsubscribedAck, ReplayResponse, RealtimeError,
    PongMessage, SubscribeRequest, UnsubscribeRequest, ReplayRequest,
    parse_client_message,
)
# smoke test parse
msg = parse_client_message({'type': 'subscribe', 'channel': 'workflow:abc'})
assert msg.channel == 'workflow:abc'
msg2 = parse_client_message({'type': 'unknown'})
assert msg2 is None
print('protocol ok')
"
```

Expected: `protocol ok`

- [ ] **Step 4: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add backend/realtime/protocol.py backend/schemas/event.py && \
  git commit -m "feat(realtime): add WebSocket wire protocol types"
```

---

## Task 2: Backend Connection Manager

**Files:**
- Fill: `backend/realtime/manager.py`

- [ ] **Step 1: Write the implementation**

```python
# backend/realtime/manager.py
"""
ConnectionManager: in-process registry of active WebSocket connections.

Each connection is identified by a UUID string (connection_id).
Thread-safety: uses asyncio.Lock since FastAPI/Starlette runs in asyncio.

Does NOT hold user state — the WS endpoint layer maps connection_id → user_id.
"""
from __future__ import annotations

import asyncio
import uuid
from typing import Any

import structlog
from fastapi import WebSocket, WebSocketDisconnect

logger = structlog.get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket) -> str:
        """Accept a WebSocket and register it. Returns connection_id."""
        await ws.accept()
        connection_id = str(uuid.uuid4())
        async with self._lock:
            self._connections[connection_id] = ws
        logger.info(
            "realtime.connection.opened",
            connection_id=connection_id,
            total=len(self._connections),
        )
        return connection_id

    async def disconnect(self, connection_id: str) -> None:
        """Remove a connection. Safe to call if already removed."""
        async with self._lock:
            self._connections.pop(connection_id, None)
        logger.info(
            "realtime.connection.closed",
            connection_id=connection_id,
            total=len(self._connections),
        )

    async def send_json(self, connection_id: str, data: dict[str, Any]) -> bool:
        """
        Send JSON to one connection. Returns True on success, False if gone.
        Removes the connection if the send fails (stale socket).
        """
        ws = self._connections.get(connection_id)
        if ws is None:
            return False
        try:
            await ws.send_json(data)
            return True
        except Exception as exc:
            logger.warning(
                "realtime.connection.send_failed",
                connection_id=connection_id,
                error=str(exc),
            )
            await self.disconnect(connection_id)
            return False

    async def broadcast_json(
        self, connection_ids: set[str], data: dict[str, Any]
    ) -> int:
        """
        Send JSON to multiple connections concurrently.
        Returns count of successful sends.
        """
        if not connection_ids:
            return 0
        results = await asyncio.gather(
            *[self.send_json(cid, data) for cid in connection_ids],
            return_exceptions=True,
        )
        return sum(1 for r in results if r is True)

    @property
    def connection_count(self) -> int:
        return len(self._connections)

    def is_connected(self, connection_id: str) -> bool:
        return connection_id in self._connections


# Module-level singleton
connection_manager = ConnectionManager()
```

- [ ] **Step 2: Validate**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/python -c "
from realtime.manager import ConnectionManager, connection_manager
import inspect, asyncio

cm = ConnectionManager()
assert cm.connection_count == 0
assert not cm.is_connected('fake-id')
assert connection_manager is not None
print('manager ok')
"
```

Expected: `manager ok`

- [ ] **Step 3: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add backend/realtime/manager.py && \
  git commit -m "feat(realtime): add ConnectionManager"
```

---

## Task 3: Backend Subscription Manager

**Files:**
- Fill: `backend/realtime/subscriptions.py`

- [ ] **Step 1: Write the implementation**

```python
# backend/realtime/subscriptions.py
"""
SubscriptionManager: maps channels to subscriber connection IDs.

Channel naming conventions:
  workflow:{workflow_id}   — per-workflow events
  lead:{lead_id}           — per-lead events
  approvals                — all approval events
  system                   — system-wide events (admin only)
  user:{user_id}           — user-specific notifications

Permission rules:
  - Any authenticated user can subscribe to workflow:{id} and lead:{id}
    for entities they have access to (scoping enforced at broadcast time
    in Phase 5; here we validate channel format only)
  - "approvals" requires role: admin or reviewer
  - "system" requires role: admin
  - "user:{id}" only the matching user or admin

This manager is purely in-memory. It does NOT touch the DB.
"""
from __future__ import annotations

import re
import structlog

logger = structlog.get_logger(__name__)

# Valid channel patterns
_CHANNEL_PATTERNS = [
    re.compile(r"^workflow:[0-9a-f-]{36}$"),
    re.compile(r"^lead:[0-9a-f-]{36}$"),
    re.compile(r"^approvals$"),
    re.compile(r"^system$"),
    re.compile(r"^user:[0-9a-f-]{36}$"),
]

# Channels that require elevated roles (checked against UserRole str values)
_RESTRICTED_CHANNELS: dict[str, set[str]] = {
    "approvals": {"admin", "reviewer"},
    "system": {"admin"},
}


def validate_channel(channel: str) -> bool:
    """Return True if the channel name matches a known pattern."""
    return any(p.match(channel) for p in _CHANNEL_PATTERNS)


def channel_allowed(channel: str, role: str) -> bool:
    """
    Check if a role may subscribe to a channel.
    Restricted channels enforce role membership.
    Non-restricted channels are open to any authenticated user.
    """
    if not validate_channel(channel):
        return False
    base = channel.split(":")[0]
    if base in _RESTRICTED_CHANNELS:
        return role in _RESTRICTED_CHANNELS[base]
    return True


class SubscriptionManager:
    def __init__(self) -> None:
        # channel → set of connection_ids
        self._channel_subs: dict[str, set[str]] = {}
        # connection_id → set of channels
        self._conn_channels: dict[str, set[str]] = {}

    def subscribe(self, connection_id: str, channel: str) -> None:
        """Add a subscription. Idempotent."""
        if channel not in self._channel_subs:
            self._channel_subs[channel] = set()
        self._channel_subs[channel].add(connection_id)

        if connection_id not in self._conn_channels:
            self._conn_channels[connection_id] = set()
        self._conn_channels[connection_id].add(channel)

        logger.info(
            "realtime.subscription.added",
            connection_id=connection_id,
            channel=channel,
        )

    def unsubscribe(self, connection_id: str, channel: str) -> None:
        """Remove one subscription. Safe to call if not subscribed."""
        self._channel_subs.get(channel, set()).discard(connection_id)
        self._conn_channels.get(connection_id, set()).discard(channel)

    def unsubscribe_all(self, connection_id: str) -> None:
        """Remove all subscriptions for a connection (called on disconnect)."""
        channels = self._conn_channels.pop(connection_id, set())
        for channel in channels:
            self._channel_subs.get(channel, set()).discard(connection_id)
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
        """Total number of (connection_id, channel) pairs."""
        return sum(len(v) for v in self._conn_channels.values())

    @property
    def channel_count(self) -> int:
        return len(self._channel_subs)


# Module-level singleton
subscription_manager = SubscriptionManager()
```

- [ ] **Step 2: Validate**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/python -c "
from realtime.subscriptions import (
    SubscriptionManager, subscription_manager,
    validate_channel, channel_allowed,
)
import uuid

# validate_channel
assert validate_channel('workflow:' + str(uuid.uuid4()))
assert validate_channel('approvals')
assert validate_channel('system')
assert not validate_channel('invalid')
assert not validate_channel('workflow:not-a-uuid')

# channel_allowed
assert channel_allowed('approvals', 'admin')
assert channel_allowed('approvals', 'reviewer')
assert not channel_allowed('approvals', 'operator')
assert not channel_allowed('system', 'operator')
assert channel_allowed('system', 'admin')
assert channel_allowed('workflow:' + str(uuid.uuid4()), 'operator')

# SubscriptionManager
sm = SubscriptionManager()
sm.subscribe('conn-1', 'approvals')
sm.subscribe('conn-1', 'system')
sm.subscribe('conn-2', 'approvals')
assert sm.subscription_count == 3
assert 'conn-1' in sm.subscribers('approvals')
assert 'conn-2' in sm.subscribers('approvals')
assert 'approvals' in sm.channels('conn-1')
sm.unsubscribe_all('conn-1')
assert 'conn-1' not in sm.subscribers('approvals')
assert sm.subscription_count == 1
print('subscriptions ok')
"
```

Expected: `subscriptions ok`

- [ ] **Step 3: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add backend/realtime/subscriptions.py && \
  git commit -m "feat(realtime): add SubscriptionManager with channel permissions"
```

---

## Task 4: Backend Broadcast Service

**Files:**
- Fill: `backend/realtime/broadcast.py`

- [ ] **Step 1: Write the implementation**

```python
# backend/realtime/broadcast.py
"""
BroadcastService: sends RealtimeEvents to all subscribers of a channel.

Composes ConnectionManager + SubscriptionManager.
Used by domain services (Phase 5+) to push events after DB mutations.
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

    async def publish_to_connection(
        self, connection_id: str, event: RealtimeEvent
    ) -> bool:
        """Send a single event directly to one connection (e.g. for replay)."""
        return await connection_manager.send_json(connection_id, event.model_dump())


# Module-level singleton
broadcast_service = BroadcastService()
```

- [ ] **Step 2: Validate**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/python -c "
from realtime.broadcast import BroadcastService, broadcast_service
from realtime.protocol import RealtimeEvent
import inspect

assert inspect.iscoroutinefunction(broadcast_service.publish)
e = RealtimeEvent(channel='approvals', event_type='approval.created', payload={'id': '123'})
assert e.type == 'event'
assert e.event_id is not None
print('broadcast ok')
"
```

Expected: `broadcast ok`

- [ ] **Step 3: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add backend/realtime/broadcast.py && \
  git commit -m "feat(realtime): add BroadcastService"
```

---

## Task 5: Backend Heartbeat & Reconnect Helpers

**Files:**
- Fill: `backend/realtime/reconnect.py`

- [ ] **Step 1: Write the implementation**

```python
# backend/realtime/reconnect.py
"""
Heartbeat and stale connection detection for the realtime runtime.

HeartbeatTracker: records the last pong received per connection.
Used by the WS endpoint to detect silent disconnects (client stopped
responding to pings without sending a WebSocketDisconnect frame).

Stale threshold: 90 seconds without a pong.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

HEARTBEAT_INTERVAL_SECONDS = 30
STALE_THRESHOLD_SECONDS = 90  # 3 missed pings


@dataclass
class HeartbeatTracker:
    _last_pong: dict[str, float] = field(default_factory=dict)

    def record_connect(self, connection_id: str) -> None:
        """Mark connection as alive at connect time."""
        self._last_pong[connection_id] = time.monotonic()

    def record_pong(self, connection_id: str) -> None:
        """Update last-alive timestamp when pong received."""
        self._last_pong[connection_id] = time.monotonic()

    def record_disconnect(self, connection_id: str) -> None:
        """Clean up on disconnect."""
        self._last_pong.pop(connection_id, None)

    def is_stale(self, connection_id: str) -> bool:
        """Return True if no pong received within STALE_THRESHOLD_SECONDS."""
        last = self._last_pong.get(connection_id)
        if last is None:
            return True
        return (time.monotonic() - last) > STALE_THRESHOLD_SECONDS

    def stale_connections(self) -> list[str]:
        """Return all connection IDs that are currently stale."""
        now = time.monotonic()
        return [
            cid
            for cid, last in self._last_pong.items()
            if (now - last) > STALE_THRESHOLD_SECONDS
        ]

    @property
    def tracked_count(self) -> int:
        return len(self._last_pong)


# Module-level singleton
heartbeat_tracker = HeartbeatTracker()
```

- [ ] **Step 2: Validate**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/python -c "
from realtime.reconnect import HeartbeatTracker, heartbeat_tracker, STALE_THRESHOLD_SECONDS
import time

t = HeartbeatTracker()
t.record_connect('conn-1')
assert not t.is_stale('conn-1')
assert t.tracked_count == 1

# Fake a stale connection by backdating its pong time
t._last_pong['conn-1'] = time.monotonic() - (STALE_THRESHOLD_SECONDS + 1)
assert t.is_stale('conn-1')
assert 'conn-1' in t.stale_connections()

t.record_disconnect('conn-1')
assert t.tracked_count == 0
# unknown connection is stale
assert t.is_stale('never-seen')
print('reconnect ok')
"
```

Expected: `reconnect ok`

- [ ] **Step 3: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add backend/realtime/reconnect.py && \
  git commit -m "feat(realtime): add HeartbeatTracker for stale detection"
```

---

## Task 6: Backend WebSocket Route

**Files:**
- Fill: `backend/api/routes/realtime.py`
- Modify: `backend/api/v1/router.py`

- [ ] **Step 1: Write the WebSocket route**

```python
# backend/api/routes/realtime.py
"""
Realtime WebSocket endpoint and HTTP observability routes.

WebSocket connect flow:
  1. Client connects to /api/v1/realtime/ws?token=<jwt>
  2. Server validates JWT → extracts user_id + role
  3. Server registers connection, sends ConnectedAck
  4. Server starts heartbeat loop (asyncio task)
  5. Server receives messages in loop, dispatches to handlers
  6. On disconnect (any cause): cleanup connections + subscriptions

HTTP routes:
  GET /api/v1/realtime/health  — basic liveness with counts
  GET /api/v1/realtime/stats   — connection/subscription metrics
"""
from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from observability.correlation import generate_correlation_id
from realtime.broadcast import broadcast_service
from realtime.manager import connection_manager
from realtime.protocol import (
    ConnectedAck,
    PingMessage,
    RealtimeError,
    RealtimeEvent,
    SubscribedAck,
    UnsubscribedAck,
    parse_client_message,
)
from realtime.reconnect import HEARTBEAT_INTERVAL_SECONDS, heartbeat_tracker
from realtime.subscriptions import channel_allowed, subscription_manager
from security.auth import decode_access_token

router = APIRouter(prefix="/realtime", tags=["realtime"])
logger = structlog.get_logger(__name__)


async def _heartbeat_loop(connection_id: str) -> None:
    """Send pings every HEARTBEAT_INTERVAL_SECONDS until connection is gone."""
    while connection_manager.is_connected(connection_id):
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        if not connection_manager.is_connected(connection_id):
            break
        ping = PingMessage()
        ok = await connection_manager.send_json(connection_id, ping.model_dump())
        if not ok:
            break


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    token: str | None = Query(default=None),
) -> None:
    # ── Auth ──────────────────────────────────────────────────────────────────
    user_id: str | None = None
    role: str = "operator"

    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            role = payload.get("role", "operator")
        except Exception:
            # Reject unauthenticated connections
            await ws.accept()
            err = RealtimeError(
                code="authentication_error",
                message="Invalid or missing token",
            )
            await ws.send_json(err.model_dump())
            await ws.close(code=4001)
            return
    else:
        # In development, allow anonymous with operator role
        # In production this should reject — enforced by config
        pass

    # ── Connect ───────────────────────────────────────────────────────────────
    connection_id = await connection_manager.connect(ws)
    heartbeat_tracker.record_connect(connection_id)
    generate_correlation_id()

    # Send connection ack
    ack = ConnectedAck(connection_id=connection_id, user_id=user_id)
    await connection_manager.send_json(connection_id, ack.model_dump())

    # Start heartbeat background task
    heartbeat_task = asyncio.create_task(_heartbeat_loop(connection_id))

    logger.info(
        "realtime.ws.connected",
        connection_id=connection_id,
        user_id=user_id,
        role=role,
    )

    # ── Message loop ──────────────────────────────────────────────────────────
    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                err = RealtimeError(code="parse_error", message="Invalid JSON")
                await connection_manager.send_json(connection_id, err.model_dump())
                continue

            msg = parse_client_message(data)
            if msg is None:
                err = RealtimeError(code="unknown_type", message=f"Unknown message type: {data.get('type')}")
                await connection_manager.send_json(connection_id, err.model_dump())
                continue

            match msg.type:
                case "pong":
                    heartbeat_tracker.record_pong(connection_id)

                case "subscribe":
                    if not channel_allowed(msg.channel, role):
                        err = RealtimeError(
                            code="permission_denied",
                            message=f"Not allowed to subscribe to {msg.channel}",
                            channel=msg.channel,
                        )
                        await connection_manager.send_json(connection_id, err.model_dump())
                    else:
                        subscription_manager.subscribe(connection_id, msg.channel)
                        ack = SubscribedAck(
                            channel=msg.channel,
                            last_event_id=msg.last_event_id,
                        )
                        await connection_manager.send_json(connection_id, ack.model_dump())

                case "unsubscribe":
                    subscription_manager.unsubscribe(connection_id, msg.channel)
                    unack = UnsubscribedAck(channel=msg.channel)
                    await connection_manager.send_json(connection_id, unack.model_dump())

                case "replay":
                    # Phase 4: return empty replay (replay from DB implemented Phase 5)
                    from realtime.protocol import ReplayResponse
                    resp = ReplayResponse(channel=msg.channel, events=[], has_more=False)
                    await connection_manager.send_json(connection_id, resp.model_dump())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error(
            "realtime.ws.error",
            connection_id=connection_id,
            error=str(exc),
        )
    finally:
        heartbeat_task.cancel()
        subscription_manager.unsubscribe_all(connection_id)
        heartbeat_tracker.record_disconnect(connection_id)
        await connection_manager.disconnect(connection_id)
        logger.info("realtime.ws.disconnected", connection_id=connection_id)


@router.get("/health")
async def realtime_health() -> dict:
    return {
        "status": "ok",
        "connections": connection_manager.connection_count,
        "subscriptions": subscription_manager.subscription_count,
    }


@router.get("/stats")
async def realtime_stats() -> dict:
    return {
        "connections": {
            "active": connection_manager.connection_count,
        },
        "subscriptions": {
            "total": subscription_manager.subscription_count,
            "channels": subscription_manager.channel_count,
        },
        "heartbeat": {
            "tracked": heartbeat_tracker.tracked_count,
            "stale": len(heartbeat_tracker.stale_connections()),
        },
    }
```

- [ ] **Step 2: Register realtime router in `backend/api/v1/router.py`**

Read current content first, then add the realtime router. The file currently has:
```python
from fastapi import APIRouter
router = APIRouter(prefix="/api/v1")

@router.get("/ping", tags=["system"])
async def v1_ping() -> dict:
    return {"status": "ok"}

from api.routes import (  # noqa: E402
    approvals, calls, leads, properties, transcripts, workflows,
)
router.include_router(leads.router, ...)
...
```

Add after the existing includes:
```python
from api.routes.realtime import router as realtime_router  # noqa: E402
router.include_router(realtime_router)
```

- [ ] **Step 3: Validate**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/python -c "
from api.main import app
routes = [r.path for r in app.routes]
ws_routes = [r for r in routes if 'realtime' in r]
print('realtime routes:', ws_routes)
assert any('/ws' in r for r in ws_routes), f'WS route missing: {routes}'
print('route registration ok')
"
```

Expected: prints realtime routes including `/ws`

- [ ] **Step 4: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add backend/api/routes/realtime.py backend/api/v1/router.py && \
  git commit -m "feat(realtime): add WebSocket endpoint with auth, heartbeat, subscriptions"
```

---

## Task 7: Backend Realtime Unit Tests

**Files:**
- Create: `backend/tests/test_realtime.py`

- [ ] **Step 1: Write the tests**

```python
# backend/tests/test_realtime.py
"""
Realtime unit tests — pure logic, no live WebSocket connections.
Tests protocol parsing, subscription management, heartbeat, and broadcast.
"""
import time
import uuid

import pytest

from realtime.protocol import (
    ConnectedAck,
    PingMessage,
    RealtimeError,
    RealtimeEvent,
    ReplayRequest,
    SubscribeRequest,
    UnsubscribeRequest,
    parse_client_message,
)
from realtime.reconnect import (
    STALE_THRESHOLD_SECONDS,
    HeartbeatTracker,
)
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
        assert not validate_channel("APPROVALS")  # case-sensitive

    def test_approvals_requires_admin_or_reviewer(self):
        assert channel_allowed("approvals", "admin")
        assert channel_allowed("approvals", "reviewer")
        assert not channel_allowed("approvals", "operator")

    def test_system_requires_admin(self):
        assert channel_allowed("system", "admin")
        assert not channel_allowed("system", "reviewer")
        assert not channel_allowed("system", "operator")

    def test_workflow_open_to_all(self):
        wf_channel = f"workflow:{uuid.uuid4()}"
        assert channel_allowed(wf_channel, "operator")
        assert channel_allowed(wf_channel, "reviewer")
        assert channel_allowed(wf_channel, "admin")

    def test_invalid_channel_always_denied(self):
        assert not channel_allowed("hacker_channel", "admin")


# ── SubscriptionManager ───────────────────────────────────────────────────────

class TestSubscriptionManager:
    def test_subscribe_and_subscribers(self):
        sm = SubscriptionManager()
        sm.subscribe("conn-1", "approvals")
        assert "conn-1" in sm.subscribers("approvals")
        assert sm.subscription_count == 1

    def test_subscribe_idempotent(self):
        sm = SubscriptionManager()
        sm.subscribe("conn-1", "approvals")
        sm.subscribe("conn-1", "approvals")
        assert sm.subscription_count == 1

    def test_multiple_subscribers(self):
        sm = SubscriptionManager()
        sm.subscribe("conn-1", "approvals")
        sm.subscribe("conn-2", "approvals")
        sm.subscribe("conn-3", "approvals")
        assert len(sm.subscribers("approvals")) == 3

    def test_unsubscribe(self):
        sm = SubscriptionManager()
        sm.subscribe("conn-1", "approvals")
        sm.unsubscribe("conn-1", "approvals")
        assert "conn-1" not in sm.subscribers("approvals")
        assert sm.subscription_count == 0

    def test_unsubscribe_all(self):
        sm = SubscriptionManager()
        sm.subscribe("conn-1", "approvals")
        sm.subscribe("conn-1", "system")
        sm.subscribe("conn-2", "approvals")
        sm.unsubscribe_all("conn-1")
        assert sm.subscription_count == 1
        assert "conn-1" not in sm.subscribers("approvals")
        assert "conn-2" in sm.subscribers("approvals")

    def test_channels_for_connection(self):
        sm = SubscriptionManager()
        sm.subscribe("conn-1", "approvals")
        sm.subscribe("conn-1", "system")
        assert sm.channels("conn-1") == {"approvals", "system"}

    def test_subscribers_returns_copy(self):
        sm = SubscriptionManager()
        sm.subscribe("conn-1", "approvals")
        subs = sm.subscribers("approvals")
        subs.add("injected")  # mutating return value
        assert "injected" not in sm.subscribers("approvals")


# ── HeartbeatTracker ──────────────────────────────────────────────────────────

class TestHeartbeatTracker:
    def test_fresh_connection_not_stale(self):
        t = HeartbeatTracker()
        t.record_connect("conn-1")
        assert not t.is_stale("conn-1")

    def test_unknown_connection_is_stale(self):
        t = HeartbeatTracker()
        assert t.is_stale("never-seen")

    def test_stale_after_threshold(self):
        t = HeartbeatTracker()
        t.record_connect("conn-1")
        t._last_pong["conn-1"] = time.monotonic() - (STALE_THRESHOLD_SECONDS + 1)
        assert t.is_stale("conn-1")
        assert "conn-1" in t.stale_connections()

    def test_pong_resets_stale(self):
        t = HeartbeatTracker()
        t.record_connect("conn-1")
        t._last_pong["conn-1"] = time.monotonic() - (STALE_THRESHOLD_SECONDS + 1)
        t.record_pong("conn-1")
        assert not t.is_stale("conn-1")

    def test_disconnect_removes(self):
        t = HeartbeatTracker()
        t.record_connect("conn-1")
        t.record_disconnect("conn-1")
        assert t.tracked_count == 0
```

- [ ] **Step 2: Run tests**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/pytest tests/test_realtime.py -v --tb=short 2>&1 | tail -30
```

Expected: all tests pass

- [ ] **Step 3: Run full backend ruff + pytest**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/ruff check . --exclude .venv --output-format=concise && \
  .venv/bin/pytest tests/ --tb=short -q 2>&1 | tail -5
```

Expected: `Found 0 errors` and all tests passing

- [ ] **Step 4: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add backend/tests/test_realtime.py && \
  git commit -m "test(realtime): add protocol, subscription, heartbeat unit tests"
```

---

## Task 8: Frontend TypeScript Types

**Files:**
- Fill: `frontend/types/websocket.ts`
- Fill: `frontend/types/event.ts`

- [ ] **Step 1: Write `frontend/types/websocket.ts`**

```typescript
// frontend/types/websocket.ts
/**
 * Wire protocol types for the Karpathys WebSocket.
 * Must stay in sync with backend/realtime/protocol.py
 */

// ── Server → Client ──────────────────────────────────────────────────────────

export interface ConnectedAck {
  type: 'connected'
  connection_id: string
  server_time: string
  user_id: string | null
}

export interface PingMessage {
  type: 'ping'
  timestamp: string
}

export interface RealtimeEvent {
  type: 'event'
  event_id: string
  channel: string
  event_type: string
  payload: Record<string, unknown>
  correlation_id: string | null
  occurred_at: string
}

export interface SubscribedAck {
  type: 'subscribed'
  channel: string
  last_event_id: string | null
}

export interface UnsubscribedAck {
  type: 'unsubscribed'
  channel: string
}

export interface ReplayResponse {
  type: 'replay'
  channel: string
  events: RealtimeEvent[]
  has_more: boolean
}

export interface RealtimeError {
  type: 'error'
  code: string
  message: string
  channel: string | null
}

export type ServerMessage =
  | ConnectedAck
  | PingMessage
  | RealtimeEvent
  | SubscribedAck
  | UnsubscribedAck
  | ReplayResponse
  | RealtimeError

// ── Client → Server ──────────────────────────────────────────────────────────

export interface PongMessage {
  type: 'pong'
  timestamp: string
}

export interface SubscribeRequest {
  type: 'subscribe'
  channel: string
  last_event_id?: string
}

export interface UnsubscribeRequest {
  type: 'unsubscribe'
  channel: string
}

export interface ReplayRequest {
  type: 'replay'
  channel: string
  from_event_id?: string
  limit?: number
}

export type ClientMessage =
  | PongMessage
  | SubscribeRequest
  | UnsubscribeRequest
  | ReplayRequest

// ── Connection status ─────────────────────────────────────────────────────────

export type WebSocketStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'disconnected'
  | 'error'

export interface ConnectionInfo {
  connection_id: string | null
  user_id: string | null
  status: WebSocketStatus
  connected_at: number | null
  reconnect_attempts: number
  last_error: string | null
}
```

- [ ] **Step 2: Write `frontend/types/event.ts`**

```typescript
// frontend/types/event.ts
/**
 * Realtime event envelope and domain event payload types.
 * event_type naming: "{entity}.{action}" e.g. "workflow.status_changed"
 */
import type { RealtimeEvent } from './websocket'

export type { RealtimeEvent }

// Known event type strings — extendable in later phases
export type KnownEventType =
  | 'workflow.created'
  | 'workflow.status_changed'
  | 'workflow.step_advanced'
  | 'lead.created'
  | 'lead.status_changed'
  | 'approval.created'
  | 'approval.resolved'
  | 'call.started'
  | 'call.ended'
  | 'transcript.created'
  | 'transcript.completed'
  | 'notification.created'
  | 'system.heartbeat'

export type EventHandler = (event: RealtimeEvent) => void

export interface ChannelSubscription {
  channel: string
  handler: EventHandler
  last_event_id: string | null
}
```

- [ ] **Step 3: Validate TypeScript compiles**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit --strict types/websocket.ts types/event.ts 2>&1
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add frontend/types/websocket.ts frontend/types/event.ts && \
  git commit -m "feat(realtime): add TypeScript wire protocol and event types"
```

---

## Task 9: Frontend WebSocket Client + Reconnect Strategy

**Files:**
- Create: `frontend/lib/websocket/client.ts`
- Create: `frontend/lib/websocket/reconnect.ts`

- [ ] **Step 1: Write `frontend/lib/websocket/reconnect.ts`**

```typescript
// frontend/lib/websocket/reconnect.ts
/**
 * Exponential backoff reconnect strategy.
 * Used by WebSocketClient to schedule reconnect attempts.
 *
 * Backoff: min(base * 2^attempt, max) + jitter
 */

export interface ReconnectConfig {
  baseDelayMs: number   // 1000
  maxDelayMs: number    // 30000
  maxAttempts: number   // 10 (0 = unlimited)
  jitterMs: number      // 500
}

export const DEFAULT_RECONNECT_CONFIG: ReconnectConfig = {
  baseDelayMs: 1000,
  maxDelayMs: 30_000,
  maxAttempts: 10,
  jitterMs: 500,
}

export function computeDelay(attempt: number, config: ReconnectConfig): number {
  const exponential = config.baseDelayMs * Math.pow(2, attempt)
  const capped = Math.min(exponential, config.maxDelayMs)
  const jitter = Math.random() * config.jitterMs
  return Math.floor(capped + jitter)
}

export function shouldReconnect(attempt: number, config: ReconnectConfig): boolean {
  if (config.maxAttempts === 0) return true
  return attempt < config.maxAttempts
}
```

- [ ] **Step 2: Write `frontend/lib/websocket/client.ts`**

```typescript
// frontend/lib/websocket/client.ts
/**
 * WebSocketClient: typed wrapper around the native browser WebSocket.
 *
 * Responsibilities:
 * - Connect with JWT token as query param
 * - Parse all incoming messages as ServerMessage
 * - Dispatch to registered handlers by message type
 * - Respond to pings automatically with pong
 * - Reconnect on close using exponential backoff
 * - Expose connection_id from ConnectedAck
 *
 * Does NOT manage subscriptions — that's RealtimeRegistry.
 */

import type { ClientMessage, ConnectedAck, PingMessage, ServerMessage, WebSocketStatus } from '@/types/websocket'
import {
  DEFAULT_RECONNECT_CONFIG,
  ReconnectConfig,
  computeDelay,
  shouldReconnect,
} from './reconnect'

type MessageHandler<T extends ServerMessage = ServerMessage> = (msg: T) => void
type StatusChangeHandler = (status: WebSocketStatus) => void

export interface WebSocketClientOptions {
  url: string
  token?: string
  reconnect?: ReconnectConfig
  onStatusChange?: StatusChangeHandler
  onMessage?: MessageHandler
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private reconnectAttempts = 0
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private destroyed = false

  private handlers = new Map<string, Set<MessageHandler<ServerMessage>>>()
  private statusHandler: StatusChangeHandler | null = null
  private globalHandler: MessageHandler | null = null

  public connectionId: string | null = null
  public status: WebSocketStatus = 'idle'

  constructor(private options: WebSocketClientOptions) {
    this.statusHandler = options.onStatusChange ?? null
    this.globalHandler = options.onMessage ?? null
  }

  connect(): void {
    if (this.destroyed) return
    this._setStatus('connecting')
    const url = this.options.token
      ? `${this.options.url}?token=${encodeURIComponent(this.options.token)}`
      : this.options.url
    this.ws = new WebSocket(url)
    this.ws.onopen = this._onOpen
    this.ws.onmessage = this._onMessage
    this.ws.onclose = this._onClose
    this.ws.onerror = this._onError
  }

  send(msg: ClientMessage): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg))
    }
  }

  disconnect(): void {
    this.destroyed = true
    this._clearReconnectTimer()
    this.ws?.close(1000, 'client_disconnect')
    this.ws = null
    this._setStatus('disconnected')
  }

  on<T extends ServerMessage>(type: T['type'], handler: MessageHandler<T>): () => void {
    if (!this.handlers.has(type)) {
      this.handlers.set(type, new Set())
    }
    this.handlers.get(type)!.add(handler as MessageHandler<ServerMessage>)
    return () => this.handlers.get(type)?.delete(handler as MessageHandler<ServerMessage>)
  }

  private _setStatus(status: WebSocketStatus): void {
    this.status = status
    this.statusHandler?.(status)
  }

  private _onOpen = (): void => {
    this.reconnectAttempts = 0
  }

  private _onMessage = (e: MessageEvent): void => {
    let msg: ServerMessage
    try {
      msg = JSON.parse(e.data as string) as ServerMessage
    } catch {
      return
    }

    // Auto-pong
    if (msg.type === 'ping') {
      this.send({ type: 'pong', timestamp: new Date().toISOString() })
    }

    // Capture connection_id
    if (msg.type === 'connected') {
      this.connectionId = (msg as ConnectedAck).connection_id
      this._setStatus('connected')
    }

    // Dispatch to type-specific handlers
    this.handlers.get(msg.type)?.forEach((h) => h(msg))

    // Global handler
    this.globalHandler?.(msg)
  }

  private _onClose = (e: CloseEvent): void => {
    this.connectionId = null
    if (this.destroyed) {
      this._setStatus('disconnected')
      return
    }
    this._setStatus('disconnected')
    const config = this.options.reconnect ?? DEFAULT_RECONNECT_CONFIG
    if (shouldReconnect(this.reconnectAttempts, config)) {
      const delay = computeDelay(this.reconnectAttempts, config)
      this.reconnectAttempts++
      this.reconnectTimer = setTimeout(() => this.connect(), delay)
    } else {
      this._setStatus('error')
    }
  }

  private _onError = (): void => {
    // error fires before close; close will handle reconnect
    this._setStatus('error')
  }

  private _clearReconnectTimer(): void {
    if (this.reconnectTimer !== null) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
  }
}
```

- [ ] **Step 3: Validate TypeScript (no browser needed — just type-check)**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit 2>&1 | grep -E "lib/websocket|types/websocket" | head -20
```

Expected: no errors in these files

- [ ] **Step 4: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add frontend/lib/websocket/client.ts frontend/lib/websocket/reconnect.ts && \
  git commit -m "feat(realtime): add WebSocketClient with auto-reconnect"
```

---

## Task 10: Frontend Realtime Dispatcher, Deduplication, Registry

**Files:**
- Create: `frontend/lib/realtime/dispatcher.ts`
- Create: `frontend/lib/realtime/deduplication.ts`
- Create: `frontend/lib/realtime/registry.ts`

- [ ] **Step 1: Write `frontend/lib/realtime/deduplication.ts`**

```typescript
// frontend/lib/realtime/deduplication.ts
/**
 * BoundedEventDeduplicator: prevents processing the same event twice.
 *
 * Uses a bounded Set (max 1000 IDs). When full, the oldest 100 IDs
 * are evicted (FIFO via insertion-order Set iteration).
 *
 * Use case: server may re-deliver events during replay or reconnect.
 */

const MAX_SIZE = 1000
const EVICT_COUNT = 100

export class BoundedEventDeduplicator {
  private seen = new Set<string>()

  /**
   * Returns true if this event_id is NEW (not seen before).
   * Side effect: marks it as seen.
   */
  accept(eventId: string): boolean {
    if (this.seen.has(eventId)) return false

    if (this.seen.size >= MAX_SIZE) {
      // Evict oldest entries (Set iteration is insertion-order)
      const iter = this.seen.values()
      for (let i = 0; i < EVICT_COUNT; i++) {
        const next = iter.next()
        if (next.done) break
        this.seen.delete(next.value)
      }
    }

    this.seen.add(eventId)
    return true
  }

  has(eventId: string): boolean {
    return this.seen.has(eventId)
  }

  get size(): number {
    return this.seen.size
  }

  clear(): void {
    this.seen.clear()
  }
}
```

- [ ] **Step 2: Write `frontend/lib/realtime/registry.ts`**

```typescript
// frontend/lib/realtime/registry.ts
/**
 * SubscriptionRegistry: tracks which channels have active handlers.
 * Used by RealtimeProvider to know what to subscribe/unsubscribe when
 * the WebSocket connects or reconnects.
 *
 * Each channel can have multiple handlers (e.g. multiple components
 * subscribed to the same workflow channel).
 */

import type { EventHandler } from '@/types/event'

export class SubscriptionRegistry {
  private registry = new Map<string, Set<EventHandler>>()
  /** last_event_id per channel — restored on reconnect subscribe */
  private lastEventIds = new Map<string, string>()

  add(channel: string, handler: EventHandler): () => void {
    if (!this.registry.has(channel)) {
      this.registry.set(channel, new Set())
    }
    this.registry.get(channel)!.add(handler)
    return () => this.remove(channel, handler)
  }

  remove(channel: string, handler: EventHandler): void {
    this.registry.get(channel)?.delete(handler)
    if (this.registry.get(channel)?.size === 0) {
      this.registry.delete(channel)
    }
  }

  dispatch(channel: string, event: import('@/types/websocket').RealtimeEvent): void {
    this.registry.get(channel)?.forEach((h) => h(event))
  }

  setLastEventId(channel: string, eventId: string): void {
    this.lastEventIds.set(channel, eventId)
  }

  getLastEventId(channel: string): string | null {
    return this.lastEventIds.get(channel) ?? null
  }

  get channels(): string[] {
    return Array.from(this.registry.keys())
  }

  hasSubscribers(channel: string): boolean {
    return (this.registry.get(channel)?.size ?? 0) > 0
  }
}
```

- [ ] **Step 3: Write `frontend/lib/realtime/dispatcher.ts`**

```typescript
// frontend/lib/realtime/dispatcher.ts
/**
 * RealtimeDispatcher: routes incoming server messages to the right handlers.
 *
 * Responsibilities:
 * - Deduplicate events using BoundedEventDeduplicator
 * - Route "event" messages to SubscriptionRegistry
 * - Route "replay" messages to replay handlers
 * - Track last_seen_event_id per channel
 * - Expose query invalidation hook so TanStack Query refetches on events
 */

import type { QueryClient } from '@tanstack/react-query'
import type { RealtimeEvent, ServerMessage } from '@/types/websocket'
import { BoundedEventDeduplicator } from './deduplication'
import { SubscriptionRegistry } from './registry'

// Map event_type prefixes to TanStack Query cache keys to invalidate
const EVENT_QUERY_INVALIDATIONS: Record<string, string[]> = {
  'workflow.': ['workflows'],
  'lead.': ['leads'],
  'approval.': ['approvals'],
  'call.': ['calls'],
  'transcript.': ['transcripts'],
  'notification.': ['notifications'],
}

function getInvalidationKeys(eventType: string): string[][] {
  const keys: string[][] = []
  for (const [prefix, queryKeys] of Object.entries(EVENT_QUERY_INVALIDATIONS)) {
    if (eventType.startsWith(prefix)) {
      queryKeys.forEach((k) => keys.push([k]))
    }
  }
  return keys
}

export class RealtimeDispatcher {
  private dedup = new BoundedEventDeduplicator()

  constructor(
    private registry: SubscriptionRegistry,
    private queryClient: QueryClient | null = null,
  ) {}

  setQueryClient(qc: QueryClient): void {
    this.queryClient = qc
  }

  dispatch(msg: ServerMessage): void {
    switch (msg.type) {
      case 'event':
        this._handleEvent(msg)
        break
      case 'replay':
        msg.events.forEach((e) => this._handleEvent(e))
        break
      default:
        // ping/pong/ack handled at WebSocketClient level
        break
    }
  }

  private _handleEvent(event: RealtimeEvent): void {
    // Deduplication gate
    if (!this.dedup.accept(event.event_id)) return

    // Update last seen
    this.registry.setLastEventId(event.channel, event.event_id)

    // Dispatch to channel handlers
    this.registry.dispatch(event.channel, event)

    // Invalidate TanStack Query caches
    if (this.queryClient) {
      getInvalidationKeys(event.event_type).forEach((key) => {
        this.queryClient!.invalidateQueries({ queryKey: key })
      })
    }
  }

  get deduplicator(): BoundedEventDeduplicator {
    return this.dedup
  }
}
```

- [ ] **Step 4: Validate TypeScript**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit 2>&1 | grep -E "lib/realtime" | head -20
```

Expected: no errors

- [ ] **Step 5: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add frontend/lib/realtime/deduplication.ts frontend/lib/realtime/registry.ts frontend/lib/realtime/dispatcher.ts && \
  git commit -m "feat(realtime): add dispatcher, deduplication, subscription registry"
```

---

## Task 11: Frontend Zustand Stores

**Files:**
- Replace: `frontend/stores/websocket.store.ts`
- Replace: `frontend/stores/realtime.store.ts`

- [ ] **Step 1: Replace `frontend/stores/websocket.store.ts`**

```typescript
// frontend/stores/websocket.store.ts
import { create } from 'zustand'
import type { WebSocketStatus } from '@/types/websocket'

export type { WebSocketStatus }

interface WebSocketState {
  status: WebSocketStatus
  connectionId: string | null
  reconnectAttempts: number
  lastConnectedAt: number | null
  lastError: string | null

  setStatus: (status: WebSocketStatus) => void
  setConnectionId: (id: string | null) => void
  setReconnectAttempts: (n: number) => void
  setLastError: (err: string | null) => void
}

export const useWebSocketStore = create<WebSocketState>()((set) => ({
  status: 'idle',
  connectionId: null,
  reconnectAttempts: 0,
  lastConnectedAt: null,
  lastError: null,

  setStatus: (status) =>
    set((s) => ({
      status,
      lastConnectedAt: status === 'connected' ? Date.now() : s.lastConnectedAt,
    })),
  setConnectionId: (connectionId) => set({ connectionId }),
  setReconnectAttempts: (reconnectAttempts) => set({ reconnectAttempts }),
  setLastError: (lastError) => set({ lastError }),
}))
```

- [ ] **Step 2: Replace `frontend/stores/realtime.store.ts`**

```typescript
// frontend/stores/realtime.store.ts
import { create } from 'zustand'
import type { RealtimeEvent } from '@/types/websocket'

const MAX_RECENT_EVENTS = 100

interface RealtimeState {
  connected: boolean
  lastEventAt: number | null
  pendingCount: number
  recentEvents: RealtimeEvent[]
  eventCount: number

  setConnected: (v: boolean) => void
  setLastEventAt: (ts: number) => void
  setPendingCount: (n: number) => void
  appendEvent: (event: RealtimeEvent) => void
  clearEvents: () => void
}

export const useRealtimeStore = create<RealtimeState>()((set) => ({
  connected: false,
  lastEventAt: null,
  pendingCount: 0,
  recentEvents: [],
  eventCount: 0,

  setConnected: (connected) => set({ connected }),
  setLastEventAt: (lastEventAt) => set({ lastEventAt }),
  setPendingCount: (pendingCount) => set({ pendingCount }),
  appendEvent: (event) =>
    set((s) => ({
      recentEvents: [event, ...s.recentEvents].slice(0, MAX_RECENT_EVENTS),
      eventCount: s.eventCount + 1,
      lastEventAt: Date.now(),
    })),
  clearEvents: () => set({ recentEvents: [], eventCount: 0 }),
}))
```

- [ ] **Step 3: Validate TypeScript**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit 2>&1 | grep -E "stores/" | head -10
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add frontend/stores/websocket.store.ts frontend/stores/realtime.store.ts && \
  git commit -m "feat(realtime): implement Zustand websocket and realtime stores"
```

---

## Task 12: Frontend Providers

**Files:**
- Replace: `frontend/providers/WebsocketProvider.tsx`
- Replace: `frontend/providers/RealtimeProvider.tsx`

- [ ] **Step 1: Replace `frontend/providers/WebsocketProvider.tsx`**

```tsx
// frontend/providers/WebsocketProvider.tsx
'use client'

import { createContext, useContext, useEffect, useRef } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { WebSocketClient } from '@/lib/websocket/client'
import { RealtimeDispatcher } from '@/lib/realtime/dispatcher'
import { SubscriptionRegistry } from '@/lib/realtime/registry'
import { useWebSocketStore } from '@/stores/websocket.store'
import { useRealtimeStore } from '@/stores/realtime.store'
import type { RealtimeEvent } from '@/types/websocket'

interface WebsocketContextValue {
  client: WebSocketClient | null
  registry: SubscriptionRegistry | null
  dispatcher: RealtimeDispatcher | null
}

const WebsocketContext = createContext<WebsocketContextValue>({
  client: null,
  registry: null,
  dispatcher: null,
})

export function useWebsocketContext(): WebsocketContextValue {
  return useContext(WebsocketContext)
}

const WS_URL =
  (typeof process !== 'undefined' && process.env.NEXT_PUBLIC_WS_URL) ||
  'ws://localhost:8000/api/v1/realtime/ws'

export function WebsocketProvider({ children }: { children: React.ReactNode }) {
  const queryClient = useQueryClient()
  const { setStatus, setConnectionId } = useWebSocketStore()
  const { setConnected, appendEvent } = useRealtimeStore()

  const clientRef = useRef<WebSocketClient | null>(null)
  const registryRef = useRef<SubscriptionRegistry | null>(null)
  const dispatcherRef = useRef<RealtimeDispatcher | null>(null)

  useEffect(() => {
    const registry = new SubscriptionRegistry()
    const dispatcher = new RealtimeDispatcher(registry, queryClient)

    // Global event handler — updates store + dispatches to registry
    const client = new WebSocketClient({
      url: WS_URL,
      onStatusChange: (status) => {
        setStatus(status)
        setConnected(status === 'connected')

        // On reconnect, re-subscribe to all active channels
        if (status === 'connected') {
          setConnectionId(client.connectionId)
          registry.channels.forEach((channel) => {
            client.send({
              type: 'subscribe',
              channel,
              last_event_id: registry.getLastEventId(channel) ?? undefined,
            })
          })
        }
      },
      onMessage: (msg) => {
        if (msg.type === 'connected') {
          setConnectionId(msg.connection_id)
        }
        if (msg.type === 'event') {
          appendEvent(msg as RealtimeEvent)
        }
        dispatcher.dispatch(msg)
      },
    })

    registryRef.current = registry
    dispatcherRef.current = dispatcher
    clientRef.current = client

    client.connect()

    return () => {
      client.disconnect()
      clientRef.current = null
    }
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <WebsocketContext.Provider
      value={{
        client: clientRef.current,
        registry: registryRef.current,
        dispatcher: dispatcherRef.current,
      }}
    >
      {children}
    </WebsocketContext.Provider>
  )
}
```

- [ ] **Step 2: Replace `frontend/providers/RealtimeProvider.tsx`**

```tsx
// frontend/providers/RealtimeProvider.tsx
'use client'

/**
 * RealtimeProvider wraps the app with realtime event awareness.
 *
 * In Phase 4, this is a thin wrapper that ensures RealtimeStore is
 * initialised. Query invalidation is handled inside WebsocketProvider's
 * dispatcher. This provider exists as a stable seam for Phase 5+ to
 * attach workflow/approval-specific reconciliation logic.
 */
export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  return <>{children}</>
}
```

- [ ] **Step 3: Validate TypeScript**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit 2>&1 | grep -E "providers/" | head -10
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add frontend/providers/WebsocketProvider.tsx frontend/providers/RealtimeProvider.tsx && \
  git commit -m "feat(realtime): implement WebsocketProvider with reconnect and query invalidation"
```

---

## Task 13: Frontend Hooks

**Files:**
- Replace: `frontend/hooks/useWebsocket.ts`
- Replace: `frontend/hooks/useRealtime.ts`

- [ ] **Step 1: Replace `frontend/hooks/useWebsocket.ts`**

```typescript
// frontend/hooks/useWebsocket.ts
'use client'

import { useWebsocketContext } from '@/providers/WebsocketProvider'
import { useWebSocketStore } from '@/stores/websocket.store'
import type { ClientMessage, WebSocketStatus } from '@/types/websocket'

export interface UseWebsocketReturn {
  status: WebSocketStatus
  connectionId: string | null
  connected: boolean
  reconnectAttempts: number
  lastError: string | null
  send: (msg: ClientMessage) => void
  disconnect: () => void
}

export function useWebsocket(): UseWebsocketReturn {
  const { client } = useWebsocketContext()
  const { status, connectionId, reconnectAttempts, lastError } = useWebSocketStore()

  return {
    status,
    connectionId,
    connected: status === 'connected',
    reconnectAttempts,
    lastError,
    send: (msg) => client?.send(msg),
    disconnect: () => client?.disconnect(),
  }
}
```

- [ ] **Step 2: Replace `frontend/hooks/useRealtime.ts`**

```typescript
// frontend/hooks/useRealtime.ts
'use client'

import { useEffect, useRef, useState } from 'react'
import { useWebsocketContext } from '@/providers/WebsocketProvider'
import { useWebSocketStore } from '@/stores/websocket.store'
import type { EventHandler } from '@/types/event'
import type { RealtimeEvent } from '@/types/websocket'

export interface UseRealtimeReturn {
  events: RealtimeEvent[]
  connected: boolean
  lastEventAt: number | null
  subscribe: () => void
  unsubscribe: () => void
}

/**
 * Subscribe to a realtime channel and receive events.
 *
 * Usage:
 *   const { events } = useRealtime('workflow:some-uuid')
 *   const { events } = useRealtime('approvals')
 */
export function useRealtime(channel: string): UseRealtimeReturn {
  const { client, registry } = useWebsocketContext()
  const status = useWebSocketStore((s) => s.status)
  const [events, setEvents] = useState<RealtimeEvent[]>([])
  const [lastEventAt, setLastEventAt] = useState<number | null>(null)
  const unsubscribeRef = useRef<(() => void) | null>(null)

  const connected = status === 'connected'

  useEffect(() => {
    if (!registry) return

    const handler: EventHandler = (event) => {
      setEvents((prev) => [event, ...prev].slice(0, 100))
      setLastEventAt(Date.now())
    }

    // Register handler in local registry
    const removeHandler = registry.add(channel, handler)
    unsubscribeRef.current = removeHandler

    // Send subscribe to server if connected
    if (connected && client) {
      client.send({
        type: 'subscribe',
        channel,
        last_event_id: registry.getLastEventId(channel) ?? undefined,
      })
    }

    return () => {
      removeHandler()
      if (connected && client) {
        client.send({ type: 'unsubscribe', channel })
      }
    }
  }, [channel, registry]) // eslint-disable-line react-hooks/exhaustive-deps

  // Re-subscribe when connection is restored
  useEffect(() => {
    if (connected && client && registry) {
      client.send({
        type: 'subscribe',
        channel,
        last_event_id: registry.getLastEventId(channel) ?? undefined,
      })
    }
  }, [connected]) // eslint-disable-line react-hooks/exhaustive-deps

  return {
    events,
    connected,
    lastEventAt,
    subscribe: () => {
      if (connected && client) {
        client.send({ type: 'subscribe', channel })
      }
    },
    unsubscribe: () => {
      if (client) client.send({ type: 'unsubscribe', channel })
      unsubscribeRef.current?.()
    },
  }
}
```

- [ ] **Step 3: Validate TypeScript**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit 2>&1 | grep -E "hooks/use(Websocket|Realtime)" | head -10
```

Expected: no errors

- [ ] **Step 4: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add frontend/hooks/useWebsocket.ts frontend/hooks/useRealtime.ts && \
  git commit -m "feat(realtime): implement useWebsocket and useRealtime hooks"
```

---

## Task 14: Frontend Realtime Components

**Files:**
- Fill: `frontend/components/realtime/RealtimeConnectionBadge.tsx`
- Fill: `frontend/components/realtime/RealtimeStatus.tsx`
- Fill: `frontend/components/realtime/RealtimeEventFeed.tsx`
- Fill: `frontend/components/realtime/EventInspector.tsx`
- Fill: `frontend/components/realtime/EventStream.tsx`
- Fill: `frontend/components/realtime/LiveActivityRail.tsx`
- Fill: `frontend/components/realtime/PresencePanel.tsx`

- [ ] **Step 1: Write `RealtimeConnectionBadge.tsx`**

```tsx
// frontend/components/realtime/RealtimeConnectionBadge.tsx
'use client'

import { cn } from '@/lib/utils'
import { useWebSocketStore } from '@/stores/websocket.store'
import type { WebSocketStatus } from '@/types/websocket'

const STATUS_CONFIG: Record<WebSocketStatus, { label: string; color: string }> = {
  idle:         { label: 'Idle',         color: 'bg-muted-foreground' },
  connecting:   { label: 'Connecting',   color: 'bg-yellow-500 animate-pulse' },
  connected:    { label: 'Live',         color: 'bg-green-500' },
  disconnected: { label: 'Disconnected', color: 'bg-red-500' },
  error:        { label: 'Error',        color: 'bg-red-600' },
}

interface RealtimeConnectionBadgeProps {
  className?: string
  showLabel?: boolean
}

export function RealtimeConnectionBadge({
  className,
  showLabel = true,
}: RealtimeConnectionBadgeProps) {
  const status = useWebSocketStore((s) => s.status)
  const config = STATUS_CONFIG[status]

  return (
    <div className={cn('flex items-center gap-1.5', className)}>
      <span className={cn('h-2 w-2 rounded-full', config.color)} />
      {showLabel && (
        <span className="text-xs text-muted-foreground">{config.label}</span>
      )}
    </div>
  )
}
```

- [ ] **Step 2: Write `RealtimeStatus.tsx`**

```tsx
// frontend/components/realtime/RealtimeStatus.tsx
'use client'

import { useWebSocketStore } from '@/stores/websocket.store'
import { useRealtimeStore } from '@/stores/realtime.store'
import { RealtimeConnectionBadge } from './RealtimeConnectionBadge'

export function RealtimeStatus() {
  const { status, connectionId, reconnectAttempts, lastConnectedAt } = useWebSocketStore()
  const { eventCount, lastEventAt } = useRealtimeStore()

  return (
    <div className="rounded-md border bg-card p-4 text-sm space-y-2">
      <div className="flex items-center justify-between">
        <span className="font-medium">Realtime Connection</span>
        <RealtimeConnectionBadge />
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-muted-foreground">
        <span>Status</span>
        <span className="text-foreground capitalize">{status}</span>
        <span>Connection ID</span>
        <span className="text-foreground font-mono text-xs truncate">
          {connectionId ? connectionId.slice(0, 12) + '…' : '—'}
        </span>
        <span>Events received</span>
        <span className="text-foreground">{eventCount}</span>
        <span>Reconnects</span>
        <span className="text-foreground">{reconnectAttempts}</span>
        <span>Last event</span>
        <span className="text-foreground">
          {lastEventAt
            ? new Date(lastEventAt).toLocaleTimeString()
            : '—'}
        </span>
        <span>Connected since</span>
        <span className="text-foreground">
          {lastConnectedAt
            ? new Date(lastConnectedAt).toLocaleTimeString()
            : '—'}
        </span>
      </div>
    </div>
  )
}
```

- [ ] **Step 3: Write `RealtimeEventFeed.tsx`**

```tsx
// frontend/components/realtime/RealtimeEventFeed.tsx
'use client'

import { useRealtimeStore } from '@/stores/realtime.store'
import { cn } from '@/lib/utils'

export function RealtimeEventFeed({ className }: { className?: string }) {
  const { recentEvents, clearEvents } = useRealtimeStore()

  return (
    <div className={cn('flex flex-col gap-2', className)}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium">Event Feed</span>
        <button
          onClick={clearEvents}
          className="text-xs text-muted-foreground hover:text-foreground transition-colors"
        >
          Clear
        </button>
      </div>
      <div className="rounded-md border bg-card divide-y max-h-96 overflow-y-auto">
        {recentEvents.length === 0 ? (
          <div className="p-4 text-center text-sm text-muted-foreground">
            No events yet. Connect and subscribe to a channel.
          </div>
        ) : (
          recentEvents.map((event) => (
            <div key={event.event_id} className="p-3 text-xs space-y-0.5">
              <div className="flex items-center justify-between">
                <span className="font-mono font-medium text-foreground">
                  {event.event_type}
                </span>
                <span className="text-muted-foreground">
                  {new Date(event.occurred_at).toLocaleTimeString()}
                </span>
              </div>
              <div className="text-muted-foreground font-mono">{event.channel}</div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Write stub components (Phase 5+ implementations)**

```tsx
// frontend/components/realtime/EventInspector.tsx
'use client'
import type { RealtimeEvent } from '@/types/websocket'
export function EventInspector({ event }: { event: RealtimeEvent | null }) {
  if (!event) return <div className="text-sm text-muted-foreground">Select an event to inspect.</div>
  return (
    <pre className="text-xs font-mono bg-muted rounded p-3 overflow-auto">
      {JSON.stringify(event, null, 2)}
    </pre>
  )
}
```

```tsx
// frontend/components/realtime/EventStream.tsx
'use client'
// Full event stream with filtering implemented in Phase 5
export function EventStream() {
  return null
}
```

```tsx
// frontend/components/realtime/LiveActivityRail.tsx
'use client'
// Live activity rail implemented in Phase 5
export function LiveActivityRail() {
  return null
}
```

```tsx
// frontend/components/realtime/PresencePanel.tsx
'use client'
// Presence panel implemented in Phase 5
export function PresencePanel() {
  return null
}
```

- [ ] **Step 5: Validate TypeScript**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit 2>&1 | grep -E "components/realtime" | head -10
```

Expected: no errors

- [ ] **Step 6: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add frontend/components/realtime/ && \
  git commit -m "feat(realtime): add RealtimeConnectionBadge, RealtimeStatus, RealtimeEventFeed"
```

---

## Task 15: Frontend Realtime Page

**Files:**
- Replace: `frontend/app/realtime/page.tsx`

- [ ] **Step 1: Write the realtime monitor page**

```tsx
// frontend/app/realtime/page.tsx
import type { Metadata } from 'next'
import { PageContainer } from '@/components/workspace/PageContainer'
import { RealtimeStatus } from '@/components/realtime/RealtimeStatus'
import { RealtimeEventFeed } from '@/components/realtime/RealtimeEventFeed'

export const metadata: Metadata = { title: 'Realtime Monitor' }

export default function RealtimePage() {
  return (
    <PageContainer
      title="Realtime Monitor"
      description="Live WebSocket event stream and connection status"
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <RealtimeStatus />
        <RealtimeEventFeed />
      </div>
    </PageContainer>
  )
}
```

- [ ] **Step 2: Validate TypeScript**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit 2>&1 | grep "app/realtime" | head -5
```

Expected: no errors

- [ ] **Step 3: Commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add frontend/app/realtime/page.tsx && \
  git commit -m "feat(realtime): update realtime monitor page"
```

---

## Task 16: Full Validation Gates

- [ ] **Backend: ruff**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/ruff check . --exclude .venv --output-format=concise
```

Expected: `All checks passed!`

- [ ] **Backend: pytest**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/pytest tests/ -q --tb=short 2>&1 | tail -5
```

Expected: all tests passing (31 Phase 3 + new realtime tests)

- [ ] **Backend: startup**

```bash
cd /Users/angelowashington/karpathys-platform/backend && \
  .venv/bin/python -c "
from api.main import app
routes = [r.path for r in app.routes]
assert any('realtime' in r for r in routes)
print('startup + routes ok')
"
```

- [ ] **Frontend: typecheck**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npx tsc --noEmit 2>&1 | tail -5
```

Expected: no errors

- [ ] **Frontend: lint**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npm run lint 2>&1 | tail -10
```

Expected: no errors (warnings acceptable)

- [ ] **Frontend: build**

```bash
cd /Users/angelowashington/karpathys-platform/frontend && \
  npm run build 2>&1 | tail -15
```

Expected: build succeeds

- [ ] **Forbidden systems check**

Verify none of these are implemented in this phase:
- Workflow execution engine: none
- Transcript intelligence: none
- Approval governance: none
- AI orchestration: none

- [ ] **Final commit**

```bash
cd /Users/angelowashington/karpathys-platform && \
  git add -A && \
  git commit -m "chore(phase4): complete Phase 4 realtime runtime validation"
```

---

## Self-Review

### Spec Coverage

| Requirement | Task |
|-------------|------|
| WebSocket endpoint | Task 6 |
| Connection manager | Task 2 |
| Session registry | Task 2 (ConnectionManager) |
| Subscription manager | Task 3 |
| Event broadcast service | Task 4 |
| Heartbeat/ping-pong | Task 5 + Task 6 |
| Stale connection cleanup | Task 5 |
| Permission-aware subscriptions | Task 3 (channel_allowed) |
| Realtime error envelopes | Task 1 (RealtimeError) |
| WS client | Task 9 |
| Reconnect runtime | Task 9 (reconnect.ts) |
| Subscription registry | Task 10 (registry.ts) |
| Event dispatcher | Task 10 (dispatcher.ts) |
| Event deduplication | Task 10 (deduplication.ts) |
| Stale status handling | Task 9 (status store) |
| Connection status store | Task 11 |
| Replay request handling | Task 6 (empty replay response) + Task 10 (dispatcher handles replay msg) |
| Realtime health indicator | Task 14 (RealtimeConnectionBadge) |
| Provider wiring | Task 12 |
| Event envelope typing | Task 8 (websocket.ts) |
| Subscription message typing | Task 8 |
| Reconnect message typing | Task 8 |
| Replay request typing | Task 8 |
| Error message typing | Task 8 |
| Query invalidation hooks | Task 10 (dispatcher.ts) |
| Duplicate event protection | Task 10 (deduplication.ts) |
| last_seen_event_id tracking | Task 10 (registry.ts) |
| Connection logs | Task 2 + Task 6 (structlog) |
| Correlation ids | Task 6 (generate_correlation_id) |
| Active session count | Task 6 (GET /realtime/stats) |
| Subscription count | Task 6 (GET /realtime/stats) |
| Reconnect count | Task 11 (store) |
| Backend unit tests | Task 7 |
| Frontend typecheck | Task 16 |
| Frontend build | Task 16 |
