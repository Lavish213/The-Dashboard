"""
Realtime WebSocket endpoint and HTTP observability routes.

WS connect flow:
  1. Client connects using a single-use, 20-second websocket ticket
  2. Server consumes ticket and loads current active database identity
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

from core.redis import get_redis
from db.session import async_session_factory
from observability.correlation import generate_correlation_id
from observability.metrics import metrics
from realtime.manager import connection_manager
from realtime.protocol import (
    ConnectedAck,
    PingMessage,
    RealtimeError,
    RealtimeEvent,
    ReplayResponse,
    SubscribedAck,
    UnsubscribedAck,
    parse_client_message,
)
from realtime.reconnect import HEARTBEAT_INTERVAL_SECONDS, heartbeat_tracker
from realtime.subscriptions import channel_allowed, subscription_manager
from security.websocket_tickets import redeem_ticket, validate_principal

router = APIRouter(prefix="/realtime", tags=["realtime"])
logger = structlog.get_logger(__name__)


async def _check_identity(connection_id: str, principal: dict, role: str) -> bool:
    try:
        validated = False
        async with asyncio.timeout(5):
            async for redis in get_redis():
                async with async_session_factory() as session:
                    await validate_principal(principal, session, redis, expected_role=role)
                    validated = True
        if not validated:
            raise RuntimeError("Realtime identity store unavailable")
        return True
    except Exception:
        subscription_manager.unsubscribe_all(connection_id)
        heartbeat_tracker.record_disconnect(connection_id)
        await connection_manager.close_connection(connection_id, code=4001)
        return False


async def _heartbeat_loop(connection_id: str, principal: dict, role: str) -> None:
    """Ping every HEARTBEAT_INTERVAL_SECONDS until connection is gone."""
    while connection_manager.is_connected(connection_id):
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        if not connection_manager.is_connected(connection_id):
            break
        if not await _check_identity(connection_id, principal, role):
            break
        ping = PingMessage()
        ok = await connection_manager.send_json(connection_id, ping.model_dump())
        if not ok:
            break


@router.websocket("/ws")
async def websocket_endpoint(
    ws: WebSocket,
    ticket: str | None = Query(default=None),
) -> None:
    # --- Auth gate — reject immediately if no token or invalid token ---
    if ticket is None:
        await ws.accept()
        err = RealtimeError(code="authentication_error", message="Missing websocket ticket")
        await ws.send_json(err.model_dump())
        await ws.close(code=4001)
        return

    user_id: str | None = None
    role: str = "operator"

    try:
        async for redis in get_redis():
            async with asyncio.timeout(5):
                async with async_session_factory() as session:
                    user, principal = await redeem_ticket(ticket, session, redis, return_claims=True)
                    user_id = str(user.id)
                    role = user.role.value
    except Exception:
        await ws.accept()
        err = RealtimeError(code="authentication_error", message="Invalid or expired token")
        await ws.send_json(err.model_dump())
        await ws.close(code=4001)
        return

    # --- Connection accepted ---
    connection_id = await connection_manager.connect(ws)
    heartbeat_tracker.record_connect(connection_id)
    metrics.ws_connections_total += 1
    generate_correlation_id()

    ack = ConnectedAck(connection_id=connection_id, user_id=user_id)
    await connection_manager.send_json(connection_id, ack.model_dump())

    heartbeat_task = asyncio.create_task(_heartbeat_loop(connection_id, principal, role))

    logger.info(
        "realtime.ws.connected",
        connection_id=connection_id,
        user_id=user_id,
        role=role,
    )

    try:
        while True:
            raw = await ws.receive_text()
            if len(raw.encode()) > 65536:
                await connection_manager.close_connection(connection_id, code=1009)
                break
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                err = RealtimeError(code="parse_error", message="Invalid JSON")
                await connection_manager.send_json(connection_id, err.model_dump())
                continue
            if not isinstance(data, dict):
                err = RealtimeError(code="parse_error", message="Message must be a JSON object")
                await connection_manager.send_json(connection_id, err.model_dump())
                continue
            if not await _check_identity(connection_id, principal, role):
                break

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
                    if not channel_allowed(msg.channel, role, user_id):
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
                    if not channel_allowed(msg.channel, role, user_id):
                        err = RealtimeError(
                            code="permission_denied",
                            message=f"Not allowed to replay {msg.channel}",
                            channel=msg.channel,
                        )
                        await connection_manager.send_json(connection_id, err.model_dump())
                    else:
                        from events.replay import replay_channel

                        async with async_session_factory() as session:
                            stored, has_more = await replay_channel(
                                session,
                                msg.channel,
                                msg.from_event_id,
                                msg.limit,
                            )
                        events = [
                            RealtimeEvent(
                                event_id=e.event_id,
                                channel=e.channel,
                                event_type=e.event_type,
                                payload=e.payload,
                                correlation_id=e.correlation_id,
                                occurred_at=e.occurred_at.isoformat(),
                                seq_num=e.seq_num,
                            )
                            for e in stored
                        ]
                        resp = ReplayResponse(channel=msg.channel, events=events, has_more=has_more)
                        await connection_manager.send_json(connection_id, resp.model_dump())

    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.error("realtime.ws.error", connection_id=connection_id, error=str(exc))
    finally:
        heartbeat_task.cancel()
        await asyncio.gather(heartbeat_task, return_exceptions=True)
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
