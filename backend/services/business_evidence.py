import hashlib
import json
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import select

from models.lead import Lead
from services.voice_ingest import find_call, resolve_lead


def validate_snapshot(body):
    snapshot = body.get("snapshot")
    if not isinstance(snapshot, dict) or snapshot.get("schema_version") != 1 or type(snapshot.get("schema_version")) is not int or snapshot.get("quote_authorized") is not False or snapshot.get("offer_authorized") is not False:
        raise HTTPException(422, "Invalid advisory business snapshot")
    if not isinstance(snapshot.get("property_id"), str) or not snapshot["property_id"] or len(snapshot["property_id"]) > 255:
        raise HTTPException(422, "Property identity required")
    if len(json.dumps(snapshot)) > 100000 or not isinstance(snapshot.get("comparables"), list) or len(snapshot["comparables"]) > 50 or not isinstance(snapshot.get("offers"), list) or len(snapshot["offers"]) > 20 or not isinstance(snapshot.get("appointment"), dict):
        raise HTTPException(422, "Snapshot collection budget exceeded")
    for row in snapshot["comparables"]:
        if not isinstance(row, dict) or not isinstance(row.get("source_ref"), str) or not 0 < len(row['source_ref']) <= 500:
            raise HTTPException(422, "Comparable source reference required")
        for key in ('sale_price_cents', 'adjusted_value_cents'):
            value = row.get(key)
            if value is not None and (type(value) is not int or not 0 <= value <= 10**14):
                raise HTTPException(422, "Comparable amounts must be integer cents")
    for row in snapshot["offers"]:
        if not isinstance(row, dict) or row.get('status') not in {'draft', 'sent', 'countered', 'accepted', 'rejected', 'expired'}:
            raise HTTPException(422, "Invalid offer record")
        for key in ('amount_cents', 'repairs_cents'):
            value = row.get(key)
            if value is not None and (type(value) is not int or not 0 <= value <= 10**14):
                raise HTTPException(422, "Offer amounts must be integer cents")
    valuation = snapshot.get('valuation')
    if valuation is not None:
        if not isinstance(valuation, dict) or valuation.get('lead_id') != body.get('lead_id') or valuation.get('status') != 'ready_advisory' or valuation.get('method') != 'evidence_adjusted_sales_comparison' or valuation.get('purpose') not in {'as_is', 'after_repair'} or valuation.get('quote_authorized') is not False or valuation.get('offer_authorized') is not False:
            raise HTTPException(422, "Invalid bound research valuation")
        amounts = [valuation.get(k) for k in ('supported_low_cents', 'point_cents', 'supported_high_cents')]
        if any(type(v) is not int or not 0 < v <= 10**14 for v in amounts) or amounts != sorted(amounts):
            raise HTTPException(422, "Invalid valuation amounts")
    revision = hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    if body.get('revision') != revision:
        raise HTTPException(422, "Snapshot revision mismatch")
    try:
        observed = datetime.fromisoformat(body['occurred_at'].replace('Z', '+00:00'))
        if observed.tzinfo is None or not -60 <= (datetime.now(UTC) - observed).total_seconds() <= 7 * 86400:
            raise ValueError('Invalid observation time')
    except (KeyError, ValueError, TypeError, AttributeError) as error:
        raise HTTPException(422, "Dated snapshot required") from error
    return snapshot, revision, observed.astimezone(UTC).isoformat()


async def receive_business(session, body):
    snapshot, revision, observed = validate_snapshot(body)
    identity = str(body.get('call_sid') or '')
    if identity.startswith('lead:'):
        if identity != 'lead:' + str(body.get('lead_id')):
            raise HTTPException(409, 'Lead delivery partition mismatch')
    else:
        call = await find_call(session, identity)
        if body.get('lead_id') != (call.metadata_ or {}).get('external_lead_id'):
            raise HTTPException(409, 'Call and lead binding mismatch')
    lead_id = await resolve_lead(session, body)
    if lead_id is None:
        raise HTTPException(422, "Bound lead required")
    lead = await session.get(Lead, lead_id)
    metadata = dict(lead.metadata_ or {})
    receipts = dict(metadata.get('business_receipts') or {})
    identity = str(body.get('call_sid') or '')
    if not 0 < len(identity) <= 255:
        raise HTTPException(422, "Delivery partition required")
    key = hashlib.sha256((identity + ':' + revision).encode()).hexdigest()
    if key in receipts:
        return {**receipts[key], 'duplicate': True}
    if len(receipts) >= 5000:
        raise HTTPException(409, "Business snapshot receipt budget exhausted")
    current = metadata.get('business_evidence') or {}
    if current and current['snapshot']['property_id'] != snapshot['property_id']:
        raise HTTPException(409, 'Canonical property binding changed; review required')
    if current.get('observed_at', '') > observed:
        status = 'ignored_older_snapshot'
    else:
        status = 'ok'
        metadata['business_evidence'] = {'snapshot': snapshot, 'revision': revision, 'observed_at': observed}
        for field in ('address', 'city', 'state'):
            value = snapshot.get(field)
            if value is not None and (not isinstance(value, str) or len(value) > 500):
                raise HTTPException(422, "Invalid property label")
            setattr(lead, field, value)
    result = {'schema_version': 1, 'persisted': True, 'receipt_id': str(lead_id) + ':business:' + key, 'call_sid': identity, 'lead_id': str(lead_id), 'status': status}
    receipts[key] = result
    metadata['business_receipts'] = receipts
    lead.metadata_ = metadata
    await session.commit()
    return result


async def read_business(session, lead_id):
    lead = await session.scalar(select(Lead).where(Lead.id == lead_id, Lead.deleted_at.is_(None)))
    if lead is None:
        raise HTTPException(404, "Lead not found")
    evidence = (lead.metadata_ or {}).get('business_evidence')
    if not evidence:
        return {'status': 'unavailable', 'snapshot': None}
    age = (datetime.now(UTC) - datetime.fromisoformat(evidence['observed_at'])).total_seconds()
    return {'status': 'current' if 0 <= age <= 86400 else 'stale', **evidence}
