import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from fastapi import HTTPException

from models.lead import Lead
from services.source_commands import stage_callback
from services.source_operations import source_operations


def source_lead():
    external, prop, tenant = str(uuid4()), str(uuid4()), str(uuid4())
    snapshot = {
        "tenant_id": tenant,
        "property_id": prop,
        "source_updated_at": datetime.now(UTC).isoformat(),
        "appointment": {
            "at": (datetime.now(UTC) + timedelta(days=1)).isoformat(),
            "status": "confirmed",
        },
        "callback_at": None,
        "offers": [{"id": "offer", "status": "draft", "amount_cents": 25000000}],
        "followups": [],
        "email_replies": [
            {
                "id": "reply",
                "at": datetime.now(UTC).isoformat(),
                "text": "Tuesday works",
            }
        ],
        "valuation": None,
    }
    revision = hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()
    return Lead(
        full_name="Synthetic seller",
        metadata_={
            "external_source": "rei",
            "external_lead_id": external,
            "business_evidence": {
                "snapshot": snapshot,
                "revision": revision,
                "observed_at": datetime.now(UTC).isoformat(),
            },
        },
    )


async def test_source_views_keep_appointments_offers_and_replies_distinct(db):
    lead = source_lead()
    db.add(lead)
    await db.flush()
    assert source_operations(lead, "calendar")[0]["kind"] == "walkthrough"
    assert source_operations(lead, "deals")[0]["amount_cents"] == 25000000
    assert source_operations(lead, "followups")[0]["text"] == "Tuesday works"
    lead.metadata_ = {**lead.metadata_, 'source_commands': {'command': {'state': 'requires_review', 'payload': {'at': datetime.now(UTC).isoformat()}, 'error':'source_rejected'}}}
    command = source_operations(lead, 'calendar')[-1]
    assert command['kind'] == 'callback_command' and command['state'] == 'requires_review'
    assert command['text'] == 'source_rejected'
    lead.deleted_at = datetime.now(UTC)


async def test_callback_queue_replay_stale_binding_and_receipt(db, monkeypatch):
    monkeypatch.setenv("REI_COMMAND_URL", "https://source.example.invalid")
    monkeypatch.setenv("SOURCE_COMMAND_SECRET", "x" * 32)
    lead = source_lead()
    db.add(lead)
    await db.flush()
    request = uuid4()
    actor = uuid4()
    at = datetime.now(UTC) + timedelta(days=1)
    revision = lead.metadata_["business_evidence"]["revision"]
    first = await stage_callback(db, lead.id, request, at, revision, actor)
    replay = await stage_callback(db, lead.id, request, at, revision, actor)
    assert first["state"] == "pending" and replay["duplicate"]
    with pytest.raises(HTTPException):
        await stage_callback(
            db, lead.id, request, at + timedelta(hours=1), revision, actor
        )
    await db.rollback()


@pytest.mark.parametrize("action", ["schedule_callback", "set_disposition", "cancel_walkthrough", "draft_offer"])
async def test_source_command_recovers_after_outage_without_false_confirmation(
    db, monkeypatch, action
):
    from contextlib import asynccontextmanager

    from services import source_commands

    monkeypatch.setenv("REI_COMMAND_URL", "https://source.example.invalid")
    monkeypatch.setenv("SOURCE_COMMAND_SECRET", "x" * 32)
    lead = source_lead()
    db.add(lead)
    await db.flush()
    identity = uuid4()
    if action == "schedule_callback":
        await stage_callback(db, lead.id, identity, datetime.now(UTC)+timedelta(days=1), lead.metadata_["business_evidence"]["revision"], uuid4())
    else:
        details = {"set_disposition": {"disposition":"DEAD"}, "cancel_walkthrough": {"starts_at":lead.metadata_["business_evidence"]["snapshot"]["appointment"]["at"]}, "draft_offer": {"amount_cents":25000000,"repair_cents":2500000,"arv_cents":None}}
        await source_commands.stage_operation(db, lead.id, identity, lead.metadata_["business_evidence"]["revision"], uuid4(), action, details[action], "Reviewed exact source record")


    @asynccontextmanager
    async def factory():
        yield db

    monkeypatch.setattr(source_commands, "async_session_factory", factory)
    replies = []

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            return False

        async def post(self, url, json, headers):
            assert url.endswith("/operations/callback" if action == "schedule_callback" else "/operations/command")
            replies.append(json)
            if len(replies) == 1:
                return __import__("httpx").Response(503)
            return __import__("httpx").Response(
                200,
                json={
                    "schema_version": 1,
                    "persisted": True,
                    "receipt_id": json["id"],
                    "lead_id": json["lead_id"],
                    "action": action,
                },
            )

    monkeypatch.setattr(source_commands.httpx, "AsyncClient", lambda **kwargs: Client())
    await source_commands.recover_commands()
    assert lead.metadata_["source_commands"][str(identity)]["state"] == "pending"
    await source_commands.recover_commands()
    assert lead.metadata_["source_commands"][str(identity)]["state"] == "applied"
    await source_commands.recover_commands()
    assert len(replies) == 2 and replies[0] == replies[1]


@pytest.mark.parametrize('action,data', [('set_disposition',{'disposition':'DEAD'}),('draft_offer',{'amount_cents':25000000,'repair_cents':2500000,'arv_cents':None})])
async def test_guarded_operation_staging_replay_and_projection(db, monkeypatch, action, data):
    from services.source_commands import stage_operation
    monkeypatch.setenv('REI_COMMAND_URL','https://source.example.invalid')
    monkeypatch.setenv('SOURCE_COMMAND_SECRET','x'*32)
    lead=source_lead()
    db.add(lead)
    await db.flush()
    identity,actor=uuid4(),uuid4()
    revision=lead.metadata_['business_evidence']['revision']
    queued=await stage_operation(db,lead.id,identity,revision,actor,action,data,'Reviewed exact source evidence')
    replay=await stage_operation(db,lead.id,identity,revision,actor,action,data,'Reviewed exact source evidence')
    assert queued['state']=='pending' and replay['duplicate']
    saved=lead.metadata_['source_commands'][str(identity)]
    assert saved['payload']['actor_id']==str(actor) and saved['action']==action
    view='deals' if action=='draft_offer' else 'followups'
    projected=source_operations(lead,view)
    assert any(item['kind']==action+'_command' and item['state']=='pending' for item in projected)
    with pytest.raises(HTTPException):
        await stage_operation(db,lead.id,identity,revision,actor,action,data,'Changed review reason invalidates replay')
