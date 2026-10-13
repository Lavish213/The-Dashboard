from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import func, select

from api.routes import ingest, sophia_bridge
from db.session import get_session
from models.call import Call
from models.enums import LeadStatus, SophiaChannelType, SophiaSessionStatus
from models.lead import Lead
from models.sophia_session import SophiaSession
from models.sophia_turn import SophiaTurn
from models.transcript import Transcript
from models.transcript_chunk import TranscriptChunk
from security.webhooks import verify_karpathys_secret


def application(db):
    app = FastAPI()
    app.include_router(ingest.router, prefix="/api/v1/ingest")
    app.include_router(sophia_bridge.router, prefix="/api/v1/sophia")

    async def database():
        yield db

    app.dependency_overrides[get_session] = database
    app.dependency_overrides[verify_karpathys_secret] = lambda: None
    return app


async def test_external_lead_is_mapped_to_a_distinct_local_entity_and_call_replay_is_stable(db):
    external = str(uuid4())
    body = {"call_sid": "mapping-" + external, "lead_id": external, "lead_name": "Synthetic seller", "phone": "+12095550101"}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url="http://test") as client:
        first = await client.post("/api/v1/ingest/call", json=body)
        replay = await client.post("/api/v1/ingest/call", json={**body, "occurred_at": datetime.now(UTC).isoformat()})
        conflict = await client.post("/api/v1/ingest/call", json={**body, "lead_id": str(uuid4())})
    assert first.status_code == replay.status_code == 200
    data = first.json()
    assert data["persisted"] and data["lead_id"] != external and data["session_id"]
    assert replay.json()["receipt_id"] == data["receipt_id"] and replay.json()["duplicate"]
    assert conflict.status_code == 409
    assert (await db.scalar(select(func.count()).select_from(Call))) == 1
    local = await db.get(Lead, UUID(data["lead_id"]))
    assert local.metadata_["external_lead_id"] == external and local.lead_status == LeadStatus.new


async def test_turns_bind_exact_call_even_when_another_session_for_same_lead_is_newer(db):
    sid = "exact-" + str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url="http://test") as client:
        created = (await client.post("/api/v1/ingest/call", json={"call_sid": sid, "lead_id": str(uuid4())})).json()
        other = SophiaSession(session_key=str(uuid4()), lead_id=UUID(created["lead_id"]), channel=SophiaChannelType.phone, status=SophiaSessionStatus.active, channel_metadata={"call_sid": "different-call"})
        db.add(other)
        await db.flush()
        body = {"call_sid": sid, "speaker": "user", "text": "Please call tomorrow", "turn_index": 0}
        first = await client.post("/api/v1/ingest/turn", json=body)
        repeated = await client.post("/api/v1/ingest/turn", json=body)
        conflicting = await client.post("/api/v1/ingest/turn", json={**body, "text": "Different text"})
    assert first.status_code == repeated.status_code == 200 and conflicting.status_code == 409
    turn = await db.get(SophiaTurn, UUID(first.json()["turn_id"]))
    assert str(turn.session_id) == created["session_id"] and turn.session_id != other.id
    assert turn.input_payload["text"] == body["text"]
    assert (await db.scalar(select(func.count()).select_from(SophiaTurn))) == 1


async def test_transcript_chunks_are_persisted_and_deduplicated(db):
    sid, external = str(uuid4()), str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url="http://test") as client:
        await client.post("/api/v1/ingest/call", json={"call_sid": sid, "lead_id": external})
        body = {"call_sid": sid, "lead_id": external, "chunk_count": 2, "chunks": [{"speaker": "user", "text": "Hello"}, {"speaker": "sophia", "text": "Hi, I'm an AI assistant"}]}
        first = await client.post("/api/v1/ingest/transcript", json=body)
        duplicate = await client.post("/api/v1/ingest/transcript", json=body)
        wrong = await client.post("/api/v1/ingest/transcript", json={**body, "lead_id": str(uuid4())})
    assert first.status_code == duplicate.status_code == 200 and wrong.status_code == 409
    assert (await db.scalar(select(func.count()).select_from(Transcript))) == 1
    chunks = (await db.scalars(select(TranscriptChunk).order_by(TranscriptChunk.chunk_index))).all()
    assert [chunk.text for chunk in chunks] == ["Hello", "Hi, I'm an AI assistant"]


@pytest.mark.parametrize("endpoint,body", [
    ("complete", {}), ("ended", {}), ("failed", {}),
    ("turn", {"speaker": "user", "text": "Hello", "turn_index": 0}),
    ("transcript", {"chunk_count": 1, "chunks": [{"speaker": "user", "text": "Hello"}]}),
])
async def test_unknown_calls_never_receive_success_receipts(db, endpoint, body):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url="http://test") as client:
        response = await client.post("/api/v1/ingest/" + endpoint, json={"call_sid": "missing", **body})
    assert response.status_code == 404 and not response.json().get("persisted")


async def test_disposition_only_persists_an_advisory_proposal(db):
    sid = str(uuid4())
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url="http://test") as client:
        created = (await client.post("/api/v1/ingest/call", json={"call_sid": sid, "lead_id": str(uuid4())})).json()
        response = await client.post("/api/v1/sophia/disposition-action", json={"call_sid": sid, "disposition": "HOT"})
        completed = await client.post("/api/v1/ingest/complete", json={"call_sid": sid, "disposition": "qualified"})
    assert response.json()["status"] == "pending_approval" and response.json()["actions_taken"] == []
    assert completed.json()["persisted"]
    lead = await db.get(Lead, UUID(created["lead_id"]))
    assert lead.lead_status == LeadStatus.new
    call = await db.get(Call, UUID(created["call_id"]))
    assert call.metadata_["disposition_proposal"]["requires_approval"]
