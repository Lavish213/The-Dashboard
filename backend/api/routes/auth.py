from __future__ import annotations

import uuid
from datetime import UTC, datetime

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config.settings import settings
from core.redis import get_redis
from db.session import get_session
from models.enums import UserStatus
from models.user import User
from schemas.user import UserResponse
from security.rate_limits import enforce_login_budget
from security.auth import (
    blacklist_token,
    create_access_token,
    create_refresh_token,
    get_current_active_user,
    verify_password,
    verify_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_bearer = HTTPBearer(auto_error=False)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: UserResponse


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _get_raw_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> str:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return credentials.credentials


@router.post("/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
) -> LoginResponse:
    await enforce_login_budget(redis, request, body.email)
    result = await session.execute(
        select(User).where(User.email == body.email, User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if (
        user is None
        or not user.hashed_password
        or not verify_password(body.password, user.hashed_password)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status != UserStatus.active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is not active",
        )

    extra = {"role": user.role.value, "email": user.email, "sid": str(uuid.uuid4())}
    access_token = create_access_token(subject=str(user.id), extra=extra)
    refresh_token = create_refresh_token(subject=str(user.id), extra=extra)

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=UserResponse.model_validate(user),
    )


@router.post("/refresh", response_model=RefreshResponse)
async def refresh(
    body: RefreshRequest,
    redis: aioredis.Redis = Depends(get_redis),
    session: AsyncSession = Depends(get_session),
) -> RefreshResponse:
    payload = await verify_refresh_token(body.refresh_token, redis)

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        identity = uuid.UUID(user_id_str)
    except (ValueError, TypeError) as error:
        raise HTTPException(401, "Invalid refresh identity") from error
    user = await session.scalar(
        select(User).where(User.id == identity, User.deleted_at.is_(None))
    )
    if user is None or user.status != UserStatus.active:
        raise HTTPException(401, "Inactive refresh identity")
    ttl = max(1, int(payload["exp"]) - int(datetime.now(UTC).timestamp()))
    claimed = await redis.set("refresh-used:" + payload["jti"], "1", ex=ttl, nx=True)
    if not claimed:
        raise HTTPException(401, "Refresh token has already been consumed")
    await blacklist_token(payload["jti"], ttl, redis)
    extra = {"role": user.role.value, "email": user.email, "sid": payload["sid"]}
    new_access_token = create_access_token(subject=user_id_str, extra=extra)
    new_refresh_token = create_refresh_token(subject=user_id_str, extra=extra)

    return RefreshResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
    )


@router.post("/logout", status_code=status.HTTP_200_OK)
async def logout(
    user: User = Depends(get_current_active_user),
    raw_token: str = Depends(_get_raw_token),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    from jose import jwt as _jwt

    payload = _jwt.decode(
        raw_token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        options={"verify_exp": False},
    )
    sid = payload.get("sid")
    if sid:
        await redis.setex(
            "session-revoked:" + str(sid),
            settings.refresh_token_expire_days * 86400,
            "1",
        )
    jti: str | None = payload.get("jti")
    if jti:
        exp: int | None = payload.get("exp")
        ttl = (
            max(
                0,
                exp - int(datetime.now(UTC).timestamp()),
            )
            if exp
            else int(settings.access_token_expire_minutes * 60)
        )
        await blacklist_token(jti, ttl, redis)

    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_active_user),
) -> UserResponse:
    return UserResponse.model_validate(user)


@router.post("/ws-ticket")
async def websocket_ticket(
    user: User = Depends(get_current_active_user),
    raw_token: str = Depends(_get_raw_token),
    redis: aioredis.Redis = Depends(get_redis),
) -> dict:
    from security.websocket_tickets import issue_ticket

    return await issue_ticket(raw_token, user, redis)
