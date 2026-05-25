from __future__ import annotations

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
    session: AsyncSession = Depends(get_session),
) -> LoginResponse:
    result = await session.execute(select(User).where(User.email == body.email))
    user = result.scalar_one_or_none()

    if user is None or not user.hashed_password or not verify_password(body.password, user.hashed_password):
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

    extra = {"role": user.role.value, "email": user.email}
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
) -> RefreshResponse:
    payload = await verify_refresh_token(body.refresh_token, redis)

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"},
        )

    old_jti: str | None = payload.get("jti")
    if old_jti:
        exp: int | None = payload.get("exp")
        ttl = max(0, exp - int(datetime.now(UTC).timestamp())) if exp else 0
        await blacklist_token(old_jti, ttl, redis)

    extra = {"role": payload.get("role", "operator"), "email": payload.get("email", "")}
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
    jti: str | None = payload.get("jti")
    if jti:
        exp: int | None = payload.get("exp")
        ttl = max(
            0,
            exp - int(datetime.now(UTC).timestamp()),
        ) if exp else int(settings.access_token_expire_minutes * 60)
        await blacklist_token(jti, ttl, redis)

    return {"ok": True}


@router.get("/me", response_model=UserResponse)
async def get_me(
    user: User = Depends(get_current_active_user),
) -> UserResponse:
    return UserResponse.model_validate(user)