import importlib.util
import os
from pathlib import Path
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select

from api.routes import ingest, sophia_bridge
from db.session import get_session
from models.call import Call
from models.enums import LeadStatus
from models.lead import Lead
from models.transcript_chunk import TranscriptChunk


async def test_actual_rei_events_cross_the_authenticated_dashboard_boundary(db, monkeypatch):
    source = Path(os.environ["REI_REPO"]) / "backend/karpathys/events.py"
    spec = importlib.util.spec_from_file_location("rei_contract_events", source)
    producer = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(producer)
    app = FastAPI()
    app.include_router(ingest.router, prefix="/api/v1/ingest")
    app.include_router(sophia_bridge.router, prefix="/api/v1/sophia")

    async def database():
        yield db

    app.dependency_overrides[get_session] = database
    monkeypatch.setenv("KARPATHYS_WEBHOOK_SECRET", "synthetic-contract-key")
    sid, external = str(uuid4()), str(uuid4())
    chunks = [{"speaker": "SELLER", "text": "Please call back tomorrow", "sequence_order": 0, "chunk_type": "final"}, {"speaker": "SOPHIA", "text": "I can request a callback", "sequence_order": 1, "chunk_type": "final"}]
    events = [
        ("ingest/call", producer.call_created(sid, {"lead": {"id": external, "owner_first_name": "Synthetic seller", "owner_phone": "+12095550101"}})),
        ("ingest/turn", producer.turn_completed(sid, "user", chunks[0]["text"], turn_index=0)),
        ("ingest/turn", producer.turn_completed(sid, "assistant", chunks[1]["text"], turn_index=0)),
        ("ingest/transcript", producer.transcript_completed(sid, str(uuid4()), external, 2, chunks)),
        ("sophia/disposition-action", producer.disposition_action(sid, external, "HOT")),
        ("ingest/complete", producer.call_completed(sid, "HOT", 2, 80)),
        ("ingest/ended", producer.call_ended(sid)),
    ]
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.post("/api/v1/" + events[0][0], json=events[0][1])
        assert denied.status_code == 401
        for route, payload in events:
            response = await client.post("/api/v1/" + route, json=payload, headers={"X-Karpathys-Secret": "synthetic-contract-key"})
            assert response.status_code == 200, response.text
            receipt = response.json()
            assert receipt["persisted"] and receipt["schema_version"] == 1 and receipt["call_sid"] == sid
            duplicate = await client.post("/api/v1/" + route, json=payload, headers={"X-Karpathys-Secret": "synthetic-contract-key"})
            assert duplicate.json()["receipt_id"] == receipt["receipt_id"]
            assert duplicate.json()["duplicate"]
    call = await db.scalar(select(Call).where(Call.provider_call_id == sid))
    lead = await db.get(Lead, call.lead_id)
    assert lead.id != UUID(external) and lead.lead_status == LeadStatus.new
    assert call.metadata_["disposition_advisory"] == "HOT"
    assert (await db.scalar(select(func.count()).select_from(TranscriptChunk))) == 2
