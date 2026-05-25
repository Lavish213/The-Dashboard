"""
Wire protocol message types for the Karpathys realtime WebSocket.

Server → Client: connected, ping, event, subscribed, unsubscribed, replay, error
Client → Server: pong, subscribe, unsubscribe, replay
"""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, Field

# ── Server → Client ──────────────────────────────────────────────────────────

class ConnectedAck(BaseModel):
    type: Literal["connected"] = "connected"
    connection_id: str
    server_time: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    user_id: str | None = None


class PingMessage(BaseModel):
    type: Literal["ping"] = "ping"
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())


class RealtimeEvent(BaseModel):
    type: Literal["event"] = "event"
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    channel: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    correlation_id: str | None = None
    occurred_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    seq_num: int | None = None


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


# ── Client → Server ──────────────────────────────────────────────────────────

class PongMessage(BaseModel):
    type: Literal["pong"] = "pong"
    timestamp: str


class SubscribeRequest(BaseModel):
    type: Literal["subscribe"] = "subscribe"
    channel: str
    last_event_id: str | None = None


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
    """Parse raw dict into typed client message. Returns None if unknown type."""
    msg_type = data.get("type")
    try:
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
    except Exception:
        return None
