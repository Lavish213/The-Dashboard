import hashlib
import json
from uuid import uuid4

import fakeredis.aioredis
import pytest
from fastapi import HTTPException
from sqlalchemy import func, select

from api.routes.auth import RefreshRequest, refresh
from models.enums import UserRole, UserStatus
from models.lead import Lead
from models.social_lead import SocialLead
from models.user import User
from security.auth import create_refresh_token, decode_access_token
from services.instantdm import ingest_message
from services.lead_creation import create_manual_lead


async def test_legacy_manual_record_replays_across_operators(db):
    payload = {
        "source_record_id": "batch:legacy",
        "full_name": "Synthetic Owner",
        "phone": None,
        "email": None,
        "address": "123 Test St",
        "city": "Stockton",
        "state": "CA",
        "lead_source": "direct",
    }
    legacy = Lead(
        full_name=payload["full_name"],
        metadata_={
            "source_record_id": payload["source_record_id"],
            "manual_create_key": "old-actor-key",
            "manual_create_fingerprint": hashlib.sha256(
                json.dumps(payload, sort_keys=True).encode()
            ).hexdigest(),
        },
    )
    db.add(legacy)
    await db.flush()
    assert (await create_manual_lead(db, payload, str(uuid4()))).id == legacy.id
    assert (await create_manual_lead(db, payload, str(uuid4()))).id == legacy.id
    assert await db.scalar(select(func.count()).select_from(Lead)) == 1


async def test_provider_replay_is_idempotent_and_digit_text_is_not_property(db):
    body = {
        "event_id": "test-event",
        "contact": {"name": "Synthetic"},
        "messages": [{"text": "I have 123 questions"}],
    }
    first = await ingest_message(db, body)
    second = await ingest_message(db, body)
    assert first["social_lead_id"] == second["social_lead_id"] and second["duplicate"]
    assert first["intent_label"] is None and first["address_detected"] is None
    assert await db.scalar(select(func.count()).select_from(SocialLead)) == 1
    with pytest.raises(HTTPException) as error:
        await ingest_message(db, {**body, "messages": [{"text": "different"}]})
    assert error.value.status_code == 409


async def test_refresh_replay_and_session_revocation(db):
    user = User(
        email="synthetic@example.invalid",
        role=UserRole.operator,
        status=UserStatus.active,
    )
    db.add(user)
    await db.flush()
    redis = fakeredis.aioredis.FakeRedis()
    token = create_refresh_token(str(user.id))
    pair = await refresh(RefreshRequest(refresh_token=token), redis, db)
    with pytest.raises(HTTPException) as error:
        await refresh(RefreshRequest(refresh_token=token), redis, db)
    assert error.value.status_code == 401
    payload = await decode_access_token(pair.access_token, redis)
    await redis.set("session-revoked:" + payload["sid"], "1")
    with pytest.raises(HTTPException) as error:
        await decode_access_token(pair.access_token, redis)
    assert error.value.status_code == 401
