import pytest
from unittest.mock import AsyncMock

from security.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_hash_and_verify_password():
    hashed = hash_password("mysecret")
    assert verify_password("mysecret", hashed)
    assert not verify_password("wrong", hashed)
    assert hashed != "mysecret"  # not plaintext


def test_hash_is_different_each_time():
    h1 = hash_password("same")
    h2 = hash_password("same")
    assert h1 != h2  # bcrypt uses random salt


async def test_create_and_decode_token():
    token = create_access_token("user-123")
    payload = await decode_access_token(token, AsyncMock(exists=AsyncMock(return_value=0)))
    assert payload["sub"] == "user-123"
    assert "exp" in payload
    assert "iat" in payload
    assert "jti" in payload


async def test_token_with_extra_claims():
    token = create_access_token("user-456", {"role": "admin"})
    payload = await decode_access_token(token, AsyncMock(exists=AsyncMock(return_value=0)))
    assert payload["sub"] == "user-456"
    assert payload["role"] == "admin"


async def test_decode_invalid_token_raises():
    from fastapi import HTTPException
    with pytest.raises(HTTPException) as exc_info:
        await decode_access_token("not.a.valid.token", AsyncMock())
    assert exc_info.value.status_code == 401


async def test_decode_tampered_token_raises():
    from fastapi import HTTPException
    token = create_access_token("user-789")
    tampered = token[:-5] + "XXXXX"
    with pytest.raises(HTTPException) as exc_info:
        await decode_access_token(tampered, AsyncMock())
    assert exc_info.value.status_code == 401
