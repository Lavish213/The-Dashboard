from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt as _bcrypt
import redis.asyncio as aioredis
from fastapi import Depends, HTTPException, Query, WebSocketException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from core.redis import get_redis
from db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False)

_BLACKLIST_PREFIX = "blacklist:"
_REFRESH_TOKEN_TYPE = "refresh"
_ACCESS_TOKEN_TYPE = "access"


# --- Password helpers ---

def hash_password(plain: str) -> str:
    return _bcrypt.hashpw(plain.encode(), _bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode(), hashed.encode())


# --- Token creation ---

def create_access_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(minutes=settings.access_token_expire_minutes)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": _ACCESS_TOKEN_TYPE,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(subject: str, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(UTC)
    expire = now + timedelta(days=settings.refresh_token_expire_days)
    jti = str(uuid.uuid4())
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": now,
        "jti": jti,
        "type": _REFRESH_TOKEN_TYPE,
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


# --- Token decoding ---

def _decode_raw(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token,
            settings.secret_key,
            algorithms=[settings.jwt_algorithm],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def decode_access_token(
    token: str,
    redis: aioredis.Redis,
) -> dict[str, Any]:
    payload = _decode_raw(token)
    if payload.get("type") != _ACCESS_TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload.get("jti")
    if jti and await is_blacklisted(jti, redis):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


async def verify_refresh_token(
    token: str,
    redis: aioredis.Redis,
) -> dict[str, Any]:
    payload = _decode_raw(token)
    if payload.get("type") != _REFRESH_TOKEN_TYPE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )
    jti = payload.get("jti")
    if jti and await is_blacklisted(jti, redis):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return payload


# --- Redis blacklist ---

async def blacklist_token(jti: str, ttl_seconds: int, redis: aioredis.Redis) -> None:
    await redis.setex(f"{_BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")


async def is_blacklisted(jti: str, redis: aioredis.Redis) -> bool:
    result = await redis.exists(f"{_BLACKLIST_PREFIX}{jti}")
    return bool(result)


# --- FastAPI HTTP dependencies ---

async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> Any:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = await decode_access_token(credentials.credentials, redis)
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token subject",
            headers={"WWW-Authenticate": "Bearer"},
        )
    from models.user import User
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


async def get_current_active_user(
    user: Any = Depends(get_current_user),
) -> Any:
    from models.enums import UserStatus
    if user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )
    return user


# --- WebSocket dependency ---

async def get_current_user_ws(
    token: str | None = Query(default=None),
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> Any:
    if token is None:
        raise WebSocketException(code=4001, reason="Missing authentication token")
    try:
        payload = await decode_access_token(token, redis)
    except HTTPException:
        raise WebSocketException(code=4001, reason="Invalid or expired token")
    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise WebSocketException(code=4001, reason="Invalid token payload")
    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise WebSocketException(code=4001, reason="Invalid token subject")
    from models.user import User
    result = await session.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise WebSocketException(code=4001, reason="User not found")
    from models.enums import UserStatus
    if user.status != UserStatus.active:
        raise WebSocketException(code=4001, reason="User account is not active")
    return user