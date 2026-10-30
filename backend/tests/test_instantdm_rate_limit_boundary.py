import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import fakeredis.aioredis
import httpx
import pytest
from fastapi import FastAPI, HTTPException

from api.routes import instantdm_webhook
from core.redis import get_redis
from db.session import get_session
from security import rate_limits


@pytest.mark.asyncio
@pytest.mark.parametrize("fault, expected", [("limit", 429), ("outage", 503)])
async def test_webhook_rejects_before_json_and_ingestion(monkeypatch, fault, expected):
    monkeypatch.setenv("INSTANTDM_WEBHOOK_SECRET", "s" * 40)
    redis = SimpleNamespace(
        eval=AsyncMock(
            side_effect=ConnectionError("private") if fault == "outage" else None,
            return_value=6001,
        )
    )
    ingest = AsyncMock()
    monkeypatch.setattr(instantdm_webhook, "ingest_message", ingest)
    app = FastAPI()
    app.include_router(instantdm_webhook.router)
    app.dependency_overrides[get_session] = lambda: object()
    app.dependency_overrides[get_redis] = lambda: redis
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/instantdm", content=b"invalid JSON", headers={"X-InstantDM-Secret": "s" * 40}
        )
    assert response.status_code == expected
    assert "private" not in response.text
    ingest.assert_not_awaited()
    if fault == "limit":
        assert response.headers["Retry-After"] == "300"


@pytest.mark.asyncio
async def test_unauthenticated_webhook_cannot_consume_provider_budget(monkeypatch):
    monkeypatch.setenv("INSTANTDM_WEBHOOK_SECRET", "s" * 40)
    redis = SimpleNamespace(eval=AsyncMock())
    app = FastAPI()
    app.include_router(instantdm_webhook.router)
    app.dependency_overrides[get_session] = lambda: object()
    app.dependency_overrides[get_redis] = lambda: redis
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post("/instantdm", json={})
    assert response.status_code == 401
    redis.eval.assert_not_awaited()


@pytest.mark.asyncio
async def test_webhook_budget_is_atomic_under_concurrency_and_expires(monkeypatch):
    monkeypatch.setattr(rate_limits, "_INSTANTDM_EVENT_LIMIT", 5)
    redis = fakeredis.aioredis.FakeRedis()

    async def submit():
        try:
            await rate_limits.enforce_instantdm_budget(redis)
            return 200
        except HTTPException as error:
            return error.status_code

    try:
        results = await asyncio.gather(*(submit() for _ in range(20)))
        assert results.count(200) == 5
        assert results.count(429) == 15
        assert await redis.get("rate:webhook:instantdm") == b"20"
        assert 0 < await redis.ttl("rate:webhook:instantdm") <= 300
    finally:
        await redis.aclose()


@pytest.mark.asyncio
async def test_allowed_webhook_reaches_ingestion_once(monkeypatch):
    monkeypatch.setenv("INSTANTDM_WEBHOOK_SECRET", "s" * 40)
    redis = SimpleNamespace(eval=AsyncMock(return_value=1))
    ingest = AsyncMock(return_value={"status": "saved"})
    session = object()
    monkeypatch.setattr(instantdm_webhook, "ingest_message", ingest)
    app = FastAPI()
    app.include_router(instantdm_webhook.router)
    app.dependency_overrides[get_session] = lambda: session
    app.dependency_overrides[get_redis] = lambda: redis
    payload = {"event_id": "test-event"}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.post(
            "/instantdm", json=payload, headers={"X-InstantDM-Secret": "s" * 40}
        )
    assert response.status_code == 200
    ingest.assert_awaited_once_with(session, payload)
