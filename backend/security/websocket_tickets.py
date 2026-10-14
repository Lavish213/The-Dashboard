import hashlib
import json
import secrets
import time
import uuid

from fastapi import HTTPException
from sqlalchemy import select

from models.enums import UserStatus
from models.user import User
from security.auth import decode_access_token, is_blacklisted


def ticket_key(ticket):
    return "ws-ticket:" + hashlib.sha256(ticket.encode()).hexdigest()


async def issue_ticket(token, user, redis):
    payload = await decode_access_token(token, redis)
    if payload.get("sub") != str(user.id) or not payload.get("jti"):
        raise HTTPException(401, "Invalid ticket identity")
    ttl = min(20, int(payload["exp"]) - int(time.time()))
    if ttl < 1:
        raise HTTPException(401, "Expired ticket identity")
    ticket = secrets.token_urlsafe(32)
    await redis.setex(
        ticket_key(ticket),
        ttl,
        json.dumps(
            {
                "sub": payload["sub"],
                "jti": payload["jti"],
                "exp": payload["exp"],
                "sid": payload.get("sid"),
            }
        ),
    )
    return {"ticket": ticket, "expires_in": ttl}


async def validate_principal(payload, session, redis, expected_role=None):
    if payload.get("sid") and await redis.exists(
        "session-revoked:" + str(payload["sid"])
    ):
        raise HTTPException(401, "Revoked websocket session")
    if payload["exp"] <= time.time() or await is_blacklisted(payload["jti"], redis):
        raise HTTPException(401, "Revoked websocket identity")
    user = await session.scalar(
        select(User).where(
            User.id == uuid.UUID(payload["sub"]), User.deleted_at.is_(None)
        )
    )
    if user is None or user.status != UserStatus.active:
        raise HTTPException(401, "Inactive websocket identity")
    if expected_role is not None and user.role.value != expected_role:
        raise HTTPException(401, "Websocket permissions changed")
    return user


async def redeem_ticket(ticket, session, redis, return_claims=False):
    if not isinstance(ticket, str) or not 40 <= len(ticket) <= 64:
        raise HTTPException(401, "Invalid websocket ticket")
    raw = await redis.getdel(ticket_key(ticket))
    if raw is None:
        raise HTTPException(401, "Expired or consumed websocket ticket")
    payload = json.loads(raw)
    user = await validate_principal(payload, session, redis)
    return (user, payload) if return_claims else user
