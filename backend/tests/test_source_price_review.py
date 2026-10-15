from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from api.routes import source_review
from models.enums import UserRole
from security.auth import get_current_active_user


@pytest.mark.parametrize('role,expected', [(UserRole.operator,403),(UserRole.reviewer,200),(UserRole.admin,200)])
async def test_source_price_resolution_uses_authenticated_reviewer(role, expected, monkeypatch):
    actor = SimpleNamespace(id=uuid4(), role=role)
    identity = 'a'*32
    receipt = {'schema_version':1,'persisted':True,'approval_id':identity,'status':'approved','action':'resolve_price_review'}
    forward = AsyncMock(return_value=receipt)
    monkeypatch.setattr(source_review,'source_request',forward)
    app=FastAPI()
    app.include_router(source_review.router,prefix='/test')
    app.dependency_overrides[get_current_active_user]=lambda:actor
    body={'status':'approved','reason':'Reviewed comparable sales','fingerprint':'b'*64,'offer_low_cents':25000000,'offer_high_cents':27000000}
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/test/price-reviews/'+identity+'/resolve',json=body)
        invalid=await client.post('/test/price-reviews/'+identity+'/resolve',json={**body,'actor_id':str(uuid4())})
    assert response.status_code==expected
    assert invalid.status_code in {403,422}
    if expected==200:
        assert forward.call_args.args[2]['actor_id']==str(actor.id)
        assert response.json()['persisted'] is True
    else:
        forward.assert_not_called()


async def test_source_price_receipt_mismatch_denies_confirmation(monkeypatch):
    actor=SimpleNamespace(id=uuid4(),role=UserRole.reviewer)
    monkeypatch.setattr(source_review,'source_request',AsyncMock(return_value={'persisted':True,'approval_id':'wrong'}))
    app=FastAPI()
    app.include_router(source_review.router,prefix='/test')
    app.dependency_overrides[get_current_active_user]=lambda:actor
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
        response=await client.post('/test/price-reviews/'+'a'*32+'/resolve',json={'status':'rejected','reason':'Comparable evidence insufficient','fingerprint':'b'*64})
    assert response.status_code==503
