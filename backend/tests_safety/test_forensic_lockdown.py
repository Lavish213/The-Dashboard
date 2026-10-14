from types import SimpleNamespace

import fakeredis.aioredis
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from api.routes.instantdm_webhook import verify_sender
from models.enums import UserRole
from security.legacy_writes import require_legacy_writer
from security.request_limits import RequestLimits


@pytest.mark.asyncio
async def test_reviewer_cannot_write_legacy_data():
    with pytest.raises(HTTPException) as error:
        await require_legacy_writer(Request({'type': 'http', 'method': 'POST'}), SimpleNamespace(role=UserRole.reviewer))
    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_provider_secret_required(monkeypatch):
    monkeypatch.delenv('INSTANTDM_WEBHOOK_SECRET', raising=False)
    with pytest.raises(HTTPException) as error:
        verify_sender(None)
    assert error.value.status_code == 503
    monkeypatch.setenv('INSTANTDM_WEBHOOK_SECRET', 'x' * 32)
    with pytest.raises(HTTPException) as error:
        verify_sender('bad')
    assert error.value.status_code == 401
    verify_sender('x' * 32)


def test_auth_limit_is_shared_atomic_and_fails_closed(monkeypatch):
    from security import request_limits
    app = FastAPI()
    app.add_middleware(RequestLimits)
    @app.post('/api/v1/auth/login')
    async def login():
        return {'ok': True}
    client = fakeredis.aioredis.FakeRedis()
    async def redis():
        yield client
    monkeypatch.setattr(request_limits, 'get_redis', redis)
    with TestClient(app) as http:
        assert [http.post('/api/v1/auth/login').status_code for _ in range(11)] == [200] * 10 + [429]
    async def unavailable():
        raise RuntimeError('offline')
        yield
    monkeypatch.setattr(request_limits, 'get_redis', unavailable)
    with TestClient(app) as http:
        assert http.post('/api/v1/auth/login').status_code == 503
