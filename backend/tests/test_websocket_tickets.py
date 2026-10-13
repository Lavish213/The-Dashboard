import asyncio
import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
import redis.asyncio as aioredis

from security.auth import create_access_token
from security.websocket_tickets import issue_ticket, ticket_key


@pytest.mark.asyncio
async def test_real_redis_ticket_is_consumed_atomically():
    redis = aioredis.from_url(os.environ["REDIS_URL"], decode_responses=True)
    user = SimpleNamespace(id=uuid4())
    try:
        result = await issue_ticket(create_access_token(str(user.id)), user, redis)
        key = ticket_key(result["ticket"])
        assert 0 < await redis.ttl(key) <= 20
        consumed = await asyncio.gather(*(redis.getdel(key) for _ in range(40)))
        assert sum(value is not None for value in consumed) == 1
        assert await redis.getdel(key) is None
    finally:
        await redis.aclose()
