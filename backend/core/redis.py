from __future__ import annotations

from collections.abc import AsyncGenerator

import redis.asyncio as aioredis
import structlog

from config.settings import settings

logger = structlog.get_logger(__name__)

_pool: aioredis.ConnectionPool | None = None


async def init_redis() -> None:
    global _pool
    _pool = aioredis.ConnectionPool.from_url(
        settings.redis_url,
        max_connections=50,
        decode_responses=True,
        socket_timeout=5.0,
        socket_connect_timeout=5.0,
        retry_on_timeout=True,
    )
    client = aioredis.Redis(connection_pool=_pool)
    try:
        await client.ping()
        logger.info("redis.connected", url=settings.redis_url)
    except Exception as exc:
        logger.error("redis.ping_failed", error=str(exc))
        raise
    finally:
        await client.aclose()


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None
        logger.info("redis.disconnected")


async def get_redis() -> AsyncGenerator[aioredis.Redis, None]:
    if _pool is None:
        raise RuntimeError("Redis pool not initialised — call init_redis() at startup")
    client = aioredis.Redis(connection_pool=_pool)
    try:
        yield client
    finally:
        await client.aclose()