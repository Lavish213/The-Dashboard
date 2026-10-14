import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import func, select

from models.enums import LeadSource, LeadStatus
from models.lead import Lead


async def create_manual_lead(session, payload, actor_id):
    key = hashlib.sha256(("source:" + payload["source_record_id"]).encode()).hexdigest()
    fingerprint = hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode()
    ).hexdigest()
    await session.execute(
        select(
            func.pg_advisory_xact_lock(func.hashtextextended("manual-lead:" + key, 0))
        )
    )
    rows = (
        await session.scalars(
            select(Lead)
            .where(Lead.metadata_["manual_create_key"].as_string() == key)
            .limit(2)
        )
    ).all()
    if rows:
        if (
            len(rows) != 1
            or rows[0].deleted_at is not None
            or rows[0].metadata_.get("manual_create_fingerprint") != fingerprint
        ):
            raise HTTPException(
                409, "Source record already exists with different or deleted lead data"
            )
        return rows[0]
    fields = {
        key: payload[key]
        for key in ("full_name", "phone", "email", "address", "city", "state")
    }
    lead = Lead(
        **fields,
        lead_status=LeadStatus.new,
        lead_source=LeadSource(payload["lead_source"]),
        metadata_={
            "manual_create_key": key,
            "manual_create_fingerprint": fingerprint,
            "created_by": actor_id,
            "source_record_id": payload["source_record_id"],
            "source_evidence_verified": False,
        },
    )
    session.add(lead)
    await session.commit()
    await session.refresh(lead)
    return lead
