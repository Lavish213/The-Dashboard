import hmac
import os

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.redis import get_redis
from db.session import get_session
from security.rate_limits import enforce_instantdm_budget
from services.instantdm import ingest_message


def verify_sender(x_instantdm_secret: str = Header(default="")):
    secret = os.environ.get("INSTANTDM_WEBHOOK_SECRET", "")
    if len(secret) < 32:
        raise HTTPException(503, "InstantDM service authentication is not configured")
    if not hmac.compare_digest(secret.encode(), x_instantdm_secret.encode()):
        raise HTTPException(401, "Invalid provider authentication")


router = APIRouter(dependencies=[Depends(verify_sender)])


@router.post("/instantdm")
async def instantdm_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: aioredis.Redis = Depends(get_redis),
):
    await enforce_instantdm_budget(redis)
    raw = await request.body()
    if len(raw) > 64000:
        raise HTTPException(413, "Provider event budget exceeded")
    try:
        body = await request.json()
    except ValueError as error:
        raise HTTPException(422, "Valid provider JSON required") from error
    return await ingest_message(session, body)


@router.get("/instantdm/verify")
async def instantdm_verify():
    return {"status": "ok"}
