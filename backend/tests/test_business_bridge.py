import hashlib
import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import httpx
from fastapi import FastAPI
from sqlalchemy import func, select

from api.routes import ingest, leads
from db.session import get_session
from models.call import Call
from models.enums import UserRole
from models.lead import Lead
from security.auth import get_current_active_user
from security.webhooks import verify_karpathys_secret


def application(db, role=UserRole.operator):
    app = FastAPI()
    app.include_router(leads.router, prefix='/api/v1/leads')
    app.include_router(ingest.router, prefix='/api/v1/ingest')
    async def database():
        yield db
    app.dependency_overrides[get_session] = database
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=UUID('aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'), role=role)
    app.dependency_overrides[verify_karpathys_secret] = lambda: None
    return app


async def test_actual_create_route_saves_address_and_retries_without_duplicates(db):
    body = {'full_name': 'Synthetic Owner', 'source_record_id': 'batch:123', 'address': '123 Synthetic Street', 'city': 'Stockton', 'state': 'CA'}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url='http://test') as client:
        first = await client.post('/api/v1/leads', json=body)
        repeated = await client.post('/api/v1/leads', json=body)
        conflict = await client.post('/api/v1/leads', json={**body, 'address': 'Different property'})
    assert first.status_code == repeated.status_code == 201 and conflict.status_code == 409
    assert first.json()['id'] == repeated.json()['id'] and first.json()['address'] == body['address']
    assert (await db.scalar(select(func.count()).select_from(Lead))) == 1
    assert first.json()['ai_score'] is None


async def test_reviewer_cannot_create_lead(db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db, UserRole.reviewer)), base_url='http://test') as client:
        response = await client.post('/api/v1/leads', json={'full_name': 'Owner', 'source_record_id': 'x'})
    assert response.status_code == 403


def business(external):
    snapshot = {'schema_version': 1, 'property_id': 'property-1', 'address': '123 Synthetic Street', 'city': 'Stockton', 'state': 'CA', 'apn': '00123456', 'valuation': None, 'comparables': [{'sale_id': 'sale-1', 'source_ref': 'reviewed-source-1', 'closed_on': '2026-10-01', 'sale_price_cents': 45000000, 'adjusted_value_cents': 46000000}], 'offers': [{'id': 'offer-1', 'status': 'draft', 'amount_cents': 25000000, 'repairs_cents': 2000000}], 'appointment': {'at': '2026-11-01T22:00:00+00:00', 'status': 'confirmed'}, 'quote_authorized': False, 'offer_authorized': False}
    return {'call_sid': 'lead:' + external, 'lead_id': external, 'snapshot': snapshot, 'revision': hashlib.sha256(json.dumps(snapshot, sort_keys=True, separators=(',', ':')).encode()).hexdigest(), 'occurred_at': datetime.now(UTC).isoformat()}


async def test_lead_only_snapshot_is_visible_without_fabricating_a_call(db):
    external = str(uuid4())
    body = business(external)
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url='http://test') as client:
        first = await client.post('/api/v1/ingest/business', json=body)
        repeated = await client.post('/api/v1/ingest/business', json=body)
        evidence = await client.get('/api/v1/leads/' + first.json()['lead_id'] + '/business-evidence')
    assert first.status_code == repeated.status_code == evidence.status_code == 200
    assert repeated.json()['duplicate'] and repeated.json()['receipt_id'] == first.json()['receipt_id']
    snapshot = evidence.json()['snapshot']
    assert snapshot['comparables'][0]['sale_price_cents'] == 45000000
    assert snapshot['offers'][0]['amount_cents'] == 25000000 and snapshot['appointment']['status'] == 'confirmed'
    assert snapshot['offer_authorized'] is False
    assert (await db.scalar(select(func.count()).select_from(Call))) == 0


async def test_business_rejects_wrong_partition_authority_and_changed_property(db):
    body = business(str(uuid4()))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url='http://test') as client:
        wrong = await client.post('/api/v1/ingest/business', json={**body, 'call_sid': 'lead:other'})
        first = await client.post('/api/v1/ingest/business', json=body)
        changed = business(body['lead_id'])
        changed['snapshot']['property_id'] = 'different'
        changed['revision'] = hashlib.sha256(json.dumps(changed['snapshot'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        mismatch = await client.post('/api/v1/ingest/business', json=changed)
    assert first.status_code == 200 and wrong.status_code == mismatch.status_code == 409


async def test_older_snapshot_cannot_reinstate_cancelled_appointment(db):
    body = business(str(uuid4()))
    older = json.loads(json.dumps(body))
    body['snapshot']['appointment'] = {'at': None, 'status': 'cancelled'}
    body['revision'] = hashlib.sha256(json.dumps(body['snapshot'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    older['occurred_at'] = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url='http://test') as client:
        first = await client.post('/api/v1/ingest/business', json=body)
        old = await client.post('/api/v1/ingest/business', json=older)
        evidence = await client.get('/api/v1/leads/' + first.json()['lead_id'] + '/business-evidence')
    assert old.json()['status'] == 'ignored_older_snapshot'
    assert evidence.json()['snapshot']['appointment']['status'] == 'cancelled'


async def test_expired_receipts_are_pruned_before_new_snapshot(db):
    body = business(str(uuid4()))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url='http://test') as client:
        first = await client.post('/api/v1/ingest/business', json=body)
        lead = await db.get(Lead, UUID(first.json()['lead_id']))
        metadata = dict(lead.metadata_)
        metadata['business_receipts'] = {'expired': {'recorded_at': (datetime.now(UTC) - timedelta(days=8)).isoformat()}}
        lead.metadata_ = metadata
        await db.commit()
        repeated = await client.post('/api/v1/ingest/business', json=body)
    assert repeated.status_code == 200
    await db.refresh(lead)
    assert 'expired' not in lead.metadata_['business_receipts']


def priced_business(external):
    body = business(external)
    body['snapshot']['comparables'] = [{**body['snapshot']['comparables'][0], 'sale_id': f'sale-{i}'} for i in range(3)]
    body['snapshot']['valuation'] = {'schema_version': '1.0', 'lead_id': external, 'status': 'ready_advisory', 'method': 'evidence_adjusted_sales_comparison', 'purpose': 'after_repair', 'as_of': datetime.now(UTC).date().isoformat(), 'comparable_count': 3, 'supported_low_cents': 45000000, 'point_cents': 46000000, 'supported_high_cents': 47000000, 'quote_authorized': False, 'offer_authorized': False}
    body['revision'] = hashlib.sha256(json.dumps(body['snapshot'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    return body


async def test_business_rejects_stale_valuation_duplicate_comps_and_naive_appointment(db):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url='http://test') as client:
        for defect in ('stale', 'duplicate', 'count', 'naive', 'missing_time'):
            body = priced_business(str(uuid4()))
            if defect == 'stale':
                body['snapshot']['valuation']['as_of'] = (datetime.now(UTC) - timedelta(days=31)).date().isoformat()
            elif defect == 'duplicate':
                body['snapshot']['comparables'][1]['sale_id'] = 'sale-0'
            elif defect == 'count':
                body['snapshot']['valuation']['comparable_count'] = 4
            elif defect == 'naive':
                body['snapshot']['appointment']['at'] = '2026-11-01T22:00:00'
            else:
                body['snapshot']['appointment']['at'] = None
            body['revision'] = hashlib.sha256(json.dumps(body['snapshot'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
            result = await client.post('/api/v1/ingest/business', json=body)
            assert result.status_code == 422, (defect, result.text)
    assert (await db.scalar(select(func.count()).select_from(Lead))) == 0


async def test_equal_timestamp_conflict_cannot_reinstate_appointment(db):
    body = business(str(uuid4()))
    conflict = json.loads(json.dumps(body))
    conflict['snapshot']['appointment'] = {'at': None, 'status': 'cancelled'}
    conflict['revision'] = hashlib.sha256(json.dumps(conflict['snapshot'], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url='http://test') as client:
        first = await client.post('/api/v1/ingest/business', json=body)
        second = await client.post('/api/v1/ingest/business', json=conflict)
        evidence = await client.get('/api/v1/leads/' + first.json()['lead_id'] + '/business-evidence')
    assert second.status_code == 409
    assert evidence.json()['snapshot']['appointment']['status'] == 'confirmed'


async def test_recent_sync_does_not_make_expired_valuation_current(db):
    body = priced_business(str(uuid4()))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application(db)), base_url='http://test') as client:
        result = await client.post('/api/v1/ingest/business', json=body)
        assert result.status_code == 200, result.text
        lead = await db.get(Lead, UUID(result.json()['lead_id']))
        metadata = json.loads(json.dumps(lead.metadata_))
        metadata['business_evidence']['snapshot']['valuation']['as_of'] = (datetime.now(UTC) - timedelta(days=31)).date().isoformat()
        lead.metadata_ = metadata
        await db.commit()
        evidence = await client.get('/api/v1/leads/' + result.json()['lead_id'] + '/business-evidence')
    assert evidence.json()['status'] == 'stale'
