"""
Realtime WebSocket endpoint and HTTP observability routes.

WS connect flow:
  1. Client connects: /api/v1/realtime/ws?token=<jwt>
  2. Server validates JWT, extracts user_id + role
  3. Registers connection, sends ConnectedAck
  4. Starts heartbeat task
  5. Receives messages in loop, dispatches handlers
  6. On disconnect: cleanup connections + subscriptions
"""
from __future__ import annotations

import asyncio
import json

import structlog
from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from observability.correlation import generate_correlation_id
from observability.metrics import metrics
from realtime.manager import connection_manager
from realtime.protocol import (
    ConnectedAck,
    PingMessage,
    RealtimeError,
    ReplayResponse,
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
    """Ping every HEARTBEAT_INTERVAL_SECONDS until connection is gone."""
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
    user_id: str | None = None
    role: str = "operator"

    if token:
        try:
            payload = decode_access_token(token)
            user_id = payload.get("sub")
            role = payload.get("role", "operator")
        except Exception:
            await ws.accept()
            err = RealtimeError(code="authentication_error", message="Invalid or missing token")
            await ws.send_json(err.model_dump())
            await ws.close(code=4001)
            return

    connection_id = await connection_manager.connect(ws)
    heartbeat_tracker.record_connect(connection_id)
    metrics.ws_connections_total += 1
    generate_correlation_id()

    ack = ConnectedAck(connection_id=connection_id, user_id=user_id)
    await connection_manager.send_json(connection_id, ack.model_dump())

    heartbeat_task = asyncio.create_task(_heartbeat_loop(connection_id))

    logger.info(
        "realtime.ws.connected",
        connection_id=connection_id,
        user_id=user_id,
        role=role,
    )

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
                err = RealtimeError(
                    code="unknown_type",
                    message=f"Unknown message type: {data.get('type')}",
                )
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
                        sub_ack = SubscribedAck(
                            channel=msg.channel,
                            last_event_id=msg.last_event_id,
                        )
                        await connection_manager.send_json(connection_id, sub_ack.model_dump())

                case "unsubscribe":
                    subscription_manager.unsubscribe(connection_id, msg.channel)
                    unsub_ack = UnsubscribedAck(channel=msg.channel)
                    await connection_manager.send_json(connection_id, unsub_ack.model_dump())

                case "replay":
                    # Phase 4: return empty replay (DB replay implemented Phase 5+)
                    resp = ReplayResponse(channel=msg.channel, events=[], has_more=False)
                    await connection_manager.send_json(connection_id, resp.model_dump())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("realtime.ws.error", connection_id=connection_id, error=str(exc))
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
        "connections": {"active": connection_manager.connection_count},
        "subscriptions": {
            "total": subscription_manager.subscription_count,
            "channels": subscription_manager.channel_count,
        },
        "heartbeat": {
            "tracked": heartbeat_tracker.tracked_count,
            "stale": len(heartbeat_tracker.stale_connections()),
        },
    }
