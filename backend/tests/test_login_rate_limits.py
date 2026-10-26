from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from security.rate_limits import _account_key, _peer_key, enforce_login_budget


def request(host="192.0.2.15"):
    return SimpleNamespace(client=SimpleNamespace(host=host))


@pytest.mark.asyncio
async def test_login_budget_accepts_normal_attempts():
    redis = SimpleNamespace(eval=AsyncMock(side_effect=[1, 1]))
    await enforce_login_budget(redis, request(), "User@Example.com")
    assert redis.eval.await_count == 2
    assert "User@Example.com" not in str(redis.eval.await_args_list)


@pytest.mark.asyncio
async def test_login_budget_blocks_account_burst():
    redis = SimpleNamespace(eval=AsyncMock(side_effect=[11, 2]))
    with pytest.raises(HTTPException) as caught:
        await enforce_login_budget(redis, request(), "user@example.com")
    assert caught.value.status_code == 429
    assert caught.value.headers["Retry-After"] == "300"


@pytest.mark.asyncio
async def test_login_budget_blocks_peer_burst():
    redis = SimpleNamespace(eval=AsyncMock(side_effect=[2, 61]))
    with pytest.raises(HTTPException) as caught:
        await enforce_login_budget(redis, request(), "user@example.com")
    assert caught.value.status_code == 429


@pytest.mark.asyncio
async def test_login_budget_fails_closed_on_redis_outage():
    redis = SimpleNamespace(eval=AsyncMock(side_effect=ConnectionError("secret")))
    with pytest.raises(HTTPException) as caught:
        await enforce_login_budget(redis, request(), "user@example.com")
    assert caught.value.status_code == 503
    assert "secret" not in str(caught.value.detail)


def test_budget_keys_are_stable_and_do_not_expose_email_or_peer():
    assert _account_key("USER@example.com") == _account_key(" user@EXAMPLE.com ")
    assert "example.com" not in _account_key("user@example.com")
    assert "192.0.2.15" not in _peer_key(request())
    assert _peer_key(request()) != _peer_key(request("192.0.2.16"))


def test_missing_asgi_peer_is_rate_limited_without_exposing_identity():
    unknown_peer = SimpleNamespace(client=None)
    assert _peer_key(unknown_peer).startswith("rate:login:peer:")
    assert _peer_key(unknown_peer) == _peer_key(unknown_peer)
