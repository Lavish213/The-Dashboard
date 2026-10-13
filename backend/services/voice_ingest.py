import hashlib
import json
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select

from models.call import Call
from models.enums import (
    CallProvider,
    LeadSource,
    SophiaChannelType,
    SophiaSessionStatus,
)
from models.lead import Lead
from models.sophia_session import SophiaSession


def call_sid(body):
    value = body.get("call_sid")
    if not isinstance(value, str) or not value.strip() or len(value) > 255:
        raise HTTPException(422, "A bounded provider call_sid is required")
    return value


async def lock_call(session, sid):
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended("rei-call:" + sid, 0))))


async def find_call(session, sid):
    calls = (await session.scalars(select(Call).where(Call.provider == CallProvider.signalwire, Call.provider_call_id == sid, Call.deleted_at.is_(None)).limit(2))).all()
    if len(calls) != 1:
        raise HTTPException(404 if not calls else 409, "Provider call is missing or ambiguous")
    return calls[0]


def replay(call, key, body):
    fingerprint = hashlib.sha256(json.dumps({k: v for k, v in body.items() if k != "occurred_at"}, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    receipt = (call.metadata_ or {}).get("ingest_receipts", {}).get(key)
    if receipt:
        if receipt["fingerprint"] != fingerprint:
            raise HTTPException(409, "Conflicting replay for this call event")
        return {**receipt["result"], "duplicate": True}, fingerprint
    return None, fingerprint


async def acknowledge(session, call, key, fingerprint, **entities):
    metadata = dict(call.metadata_ or {})
    receipts = dict(metadata.get("ingest_receipts", {}))
    if len(receipts) >= 5000:
        raise HTTPException(409, "Call event budget exhausted")
    result = {"status": "ok", "schema_version": 1, "persisted": True, "receipt_id": f"{call.id}:{key}", "call_sid": call.provider_call_id, "call_id": str(call.id), **entities}
    receipts[key] = {"fingerprint": fingerprint, "result": result}
    metadata["ingest_receipts"] = receipts
    call.metadata_ = metadata
    await session.commit()
    return result


async def resolve_lead(session, body):
    external = body.get("lead_id")
    if external is None:
        return None
    if not isinstance(external, str) or not external or len(external) > 255:
        raise HTTPException(422, "Invalid external lead identifier")
    await session.execute(select(func.pg_advisory_xact_lock(func.hashtextextended("rei-lead:" + external, 0))))
    rows = (await session.scalars(select(Lead).where(Lead.metadata_["external_source"].as_string() == "rei", Lead.metadata_["external_lead_id"].as_string() == external).limit(2))).all()
    if len(rows) > 1 or (rows and rows[0].deleted_at is not None):
        raise HTTPException(409, "External lead mapping is ambiguous or deleted")
    if rows:
        return rows[0].id
    for field in ("lead_name", "phone", "address"):
        if body.get(field) is not None and (not isinstance(body[field], str) or len(body[field]) > 1000):
            raise HTTPException(422, "Invalid lead fields")
    lead = Lead(full_name=body.get("lead_name") or "Unverified seller", phone=body.get("phone"), address=body.get("address"), lead_source=LeadSource.imported, metadata_={"external_source": "rei", "external_lead_id": external})
    session.add(lead)
    await session.flush()
    return lead.id


async def exact_session(session, call):
    rows = (await session.scalars(select(SophiaSession).where(SophiaSession.channel_metadata["call_sid"].as_string() == call.provider_call_id).limit(2))).all()
    if len(rows) != 1:
        raise HTTPException(409, "Provider call does not have one exact Sophia session")
    return rows[0]


async def start_session(session, call):
    conversation = SophiaSession(session_key=f"rei:{call.provider_call_id}", lead_id=call.lead_id, channel=SophiaChannelType.phone, status=SophiaSessionStatus.active, started_at=datetime.now(UTC), channel_metadata={"call_sid": call.provider_call_id, "external_source": "rei"})
    session.add(conversation)
    await session.flush()
    return conversation
