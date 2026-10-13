import json
import time
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import HTTPException

from models.enums import UserStatus
from security.auth import create_access_token
from security.websocket_tickets import issue_ticket, redeem_ticket, ticket_key


@pytest.mark.asyncio
async def test_ticket_has_no_raw_token_and_is_short_lived():
    user = SimpleNamespace(id=uuid4())
    token = create_access_token(str(user.id))
    redis = AsyncMock(exists=AsyncMock(return_value=0))
    result = await issue_ticket(token, user, redis)
    key, ttl, value = redis.setex.call_args.args
    assert key == ticket_key(result["ticket"])
    assert token not in value and token not in result["ticket"]
    assert 1 <= ttl <= 20
    assert json.loads(value)["sub"] == str(user.id)


@pytest.mark.asyncio
async def test_ticket_identity_mismatch_rejected():
    redis = AsyncMock(exists=AsyncMock(return_value=0))
    with pytest.raises(HTTPException):
        await issue_ticket(create_access_token(str(uuid4())), SimpleNamespace(id=uuid4()), redis)
    redis.setex.assert_not_called()


@pytest.mark.asyncio
@pytest.mark.parametrize("fault", ["consumed", "expired", "revoked", "missing_user", "inactive", "malformed"])
async def test_invalid_ticket_does_not_authenticate(fault):
    payload = {"sub": str(uuid4()), "jti": "test-jti", "exp": time.time() + 20}
    if fault == "expired":
        payload["exp"] = time.time() - 1
    raw = None if fault == "consumed" else json.dumps(payload)
    redis = AsyncMock(getdel=AsyncMock(return_value=raw), exists=AsyncMock(return_value=fault == "revoked"))
    user = None if fault == "missing_user" else SimpleNamespace(status=UserStatus.inactive)
    session = AsyncMock(scalar=AsyncMock(return_value=user))
    with pytest.raises(HTTPException):
        await redeem_ticket("bad" if fault == "malformed" else "x" * 43, session, redis)


@pytest.mark.asyncio
async def test_ticket_loads_current_database_identity():
    user = SimpleNamespace(id=uuid4(), status=UserStatus.active, role="reviewer")
    redis = AsyncMock(getdel=AsyncMock(return_value=json.dumps({"sub": str(user.id), "jti": "test-jti", "exp": time.time() + 20})), exists=AsyncMock(return_value=0))
    session = AsyncMock(scalar=AsyncMock(return_value=user))
    assert await redeem_ticket("x" * 43, session, redis) is user
    redis.getdel.assert_awaited_once_with(ticket_key("x" * 43))


@pytest.mark.asyncio
@pytest.mark.parametrize('fault', ['expired', 'revoked', 'missing', 'inactive', 'role_changed'])
async def test_connected_identity_revalidation_rejects_changed_authorization(fault):
    from models.enums import UserRole
    from security.websocket_tickets import validate_principal
    payload = {'sub': str(uuid4()), 'jti': 'session-jti', 'exp': time.time() + 20}
    if fault == 'expired':
        payload['exp'] = time.time() - 1
    user = None if fault == 'missing' else SimpleNamespace(status=UserStatus.inactive if fault == 'inactive' else UserStatus.active, role=UserRole.operator if fault == 'role_changed' else UserRole.admin)
    redis = AsyncMock(exists=AsyncMock(return_value=fault == 'revoked'))
    session = AsyncMock(scalar=AsyncMock(return_value=user))
    with pytest.raises(HTTPException):
        await validate_principal(payload, session, redis, expected_role='admin')


@pytest.mark.asyncio
async def test_failed_connected_authentication_evicts_subscriptions(monkeypatch):
    from api.routes import realtime
    from realtime.manager import connection_manager
    from realtime.subscriptions import subscription_manager
    ws = AsyncMock()
    connection = await connection_manager.connect(ws)
    subscription_manager.subscribe(connection, 'approvals')
    async def redis():
        yield AsyncMock()
    monkeypatch.setattr(realtime, 'get_redis', redis)
    monkeypatch.setattr(realtime, 'async_session_factory', lambda: AsyncMock())
    monkeypatch.setattr(realtime, 'validate_principal', AsyncMock(side_effect=HTTPException(401, 'revoked')))
    assert not await realtime._check_identity(connection, {}, 'admin')
    assert not connection_manager.is_connected(connection)
    assert subscription_manager.subscription_count == 0
    ws.close.assert_awaited_once_with(code=4001)
