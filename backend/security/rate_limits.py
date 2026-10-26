"""Atomic, fail-closed login request budgets backed by the shared Redis instance.

The source address is the ASGI peer address, not a client-controlled forwarding
header. A trusted ingress proxy may require separate edge budgets.
"""

from __future__ import annotations

import hashlib
import hmac

import redis.asyncio as aioredis
from fastapi import HTTPException, Request

from config.settings import settings

_WINDOW_SECONDS = 300
_ACCOUNT_LIMIT = 10
_PEER_LIMIT = 60

# Redis executes the increment and expiry assignment atomically.
_BUDGET_SCRIPT = """
local count = redis.call('INCR', KEYS[1])
if count == 1 then
  redis.call('EXPIRE', KEYS[1], ARGV[1])
end
return count
"""


def _account_key(email: str) -> str:
    digest = hmac.new(
        settings.secret_key.encode(),
        email.strip().casefold().encode(),
        hashlib.sha256,
    ).hexdigest()
    return "rate:login:account:" + digest


def _peer_key(request: Request) -> str:
    peer = request.client.host if request.client else "unknown"
    digest = hmac.new(
        settings.secret_key.encode(), peer.encode(), hashlib.sha256
    ).hexdigest()
    return "rate:login:peer:" + digest


async def enforce_login_budget(
    redis: aioredis.Redis, request: Request, email: str
) -> None:
    """Reject excess attempts before any password lookup or token issuance."""
    try:
        # Check both budgets, including on an over-limit request, to avoid
        # providing a cheap bypass via alternate account identifiers.
        account_count = int(
            await redis.eval(_BUDGET_SCRIPT, 1, _account_key(email), _WINDOW_SECONDS)
        )
        peer_count = int(
            await redis.eval(_BUDGET_SCRIPT, 1, _peer_key(request), _WINDOW_SECONDS)
        )
    except Exception as error:
        raise HTTPException(
            status_code=503, detail="Authentication rate control unavailable"
        ) from error
    if account_count > _ACCOUNT_LIMIT or peer_count > _PEER_LIMIT:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again later.",
            headers={"Retry-After": str(_WINDOW_SECONDS)},
        )
