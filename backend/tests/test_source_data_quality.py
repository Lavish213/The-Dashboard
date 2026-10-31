from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from api.routes import source_review
from models.enums import UserRole
from security.auth import get_current_active_user

REPORT = {
    'schema_version': 1, 'generated_at': '2026-10-31T04:00:00+00:00', 'properties': 419, 'properties_with_comp_arv': 1,
    'properties_needing_comps': 418, 'assessed_based_arv': 0, 'comps_rows': 0, 'leads': 252, 'leads_with_phone': 1,
    'leads_with_bob_brief': 19, 'by_distress_type': {'free_and_clear': {'properties': 222, 'with_comp_arv': 0, 'needs_comps': 222}},
    'private_field': 'never forwarded',
}


def app(role):
    application = FastAPI()
    application.include_router(source_review.router, prefix='/test')
    application.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=uuid4(), role=role)
    return application


async def get(application):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url='http://test') as client:
        return await client.get('/test/data-quality')


@pytest.mark.parametrize('role', [UserRole.operator, UserRole.reviewer, UserRole.admin])
async def test_data_quality_forwards_only_known_fields(role, monkeypatch):
    forward = AsyncMock(return_value=REPORT)
    monkeypatch.setattr(source_review, 'source_request', forward)
    response = await get(app(role))
    assert response.status_code == 200
    forward.assert_awaited_once_with('GET', '/api/health/data-quality')
    body = response.json()
    assert 'private_field' not in body
    assert body['leads_with_phone'] == 1 and body['assessed_based_arv'] == 0
    assert body['by_distress_type']['free_and_clear']['needs_comps'] == 222


async def test_data_quality_rejects_unknown_schema(monkeypatch):
    monkeypatch.setattr(source_review, 'source_request', AsyncMock(return_value={**REPORT, 'schema_version': 2}))
    response = await get(app(UserRole.admin))
    assert response.status_code == 503


async def test_data_quality_forwards_only_rentcast_count(monkeypatch):
    monkeypatch.setattr(source_review, 'source_request', AsyncMock(return_value={**REPORT, 'rentcast': {'used': 7, 'hard_cap': 999, 'window_days': 2, 'secret': 'x'}}))
    body = (await get(app(UserRole.reviewer))).json()
    assert body['rentcast'] == {'used': 7, 'hard_cap': 50, 'window_days': 31}


@pytest.mark.parametrize('value', [None, 'x', {'used': True}, {'used': -1}, {'used': '7'}])
async def test_data_quality_drops_bad_rentcast(monkeypatch, value):
    monkeypatch.setattr(source_review, 'source_request', AsyncMock(return_value={**REPORT, 'rentcast': value}))
    assert (await get(app(UserRole.admin))).json()['rentcast'] is None


async def call(application, method, path, body=None):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url='http://test') as client:
        return await client.request(method, '/test' + path, json=body)


@pytest.mark.parametrize('role', [UserRole.operator, UserRole.reviewer, UserRole.admin])
async def test_rentcast_usage_is_readable_and_clamped(role, monkeypatch):
    forward = AsyncMock(return_value={'used': 12, 'hard_cap': 50, 'window_days': 31, 'enabled': True, 'configured_cap': 50, 'ok': 12})
    monkeypatch.setattr(source_review, 'source_request', forward)
    response = await call(app(role), 'GET', '/rentcast/usage')
    assert response.status_code == 200
    forward.assert_awaited_once_with('GET', '/api/operations/rentcast/usage')
    assert response.json() == {'used': 12, 'hard_cap': 50, 'window_days': 31, 'enabled': True, 'configured_cap': 50, 'remaining': 38}


@pytest.mark.parametrize('cap,remaining', [(1000, 0), (True, 0), (-5, 0), (20, 8)])
async def test_rentcast_usage_never_reports_more_than_fifty(cap, remaining, monkeypatch):
    monkeypatch.setattr(source_review, 'source_request', AsyncMock(return_value={'used': 12, 'enabled': 'true', 'configured_cap': cap}))
    body = (await call(app(UserRole.admin), 'GET', '/rentcast/usage')).json()
    assert body['remaining'] == remaining and body['enabled'] is False and body['hard_cap'] == 50


async def test_rentcast_usage_unavailable(monkeypatch):
    monkeypatch.setattr(source_review, 'source_request', AsyncMock(return_value={'used': None}))
    assert (await call(app(UserRole.admin), 'GET', '/rentcast/usage')).status_code == 503


@pytest.mark.parametrize('role', [UserRole.operator, UserRole.reviewer])
async def test_rentcast_price_is_admin_only(role, monkeypatch):
    forward = AsyncMock()
    monkeypatch.setattr(source_review, 'source_request', forward)
    response = await call(app(role), 'POST', '/rentcast/price', {'limit': 5})
    assert response.status_code == 403
    forward.assert_not_awaited()


@pytest.mark.parametrize('body', [{'limit': 0}, {'limit': 51}, {'limit': '5'}, {'limit': True}, {'limit': 2.5}, {}, {'limit': 5, 'extra': 1}])
async def test_rentcast_price_validates_limit(body, monkeypatch):
    forward = AsyncMock()
    monkeypatch.setattr(source_review, 'source_request', forward)
    assert (await call(app(UserRole.admin), 'POST', '/rentcast/price', body)).status_code == 422
    forward.assert_not_awaited()


async def test_rentcast_price_forwards_and_filters(monkeypatch):
    forward = AsyncMock(return_value={'requested': 5, 'priced': 4, 'no_data': 1, 'errors': 0, 'comps_saved': 60, 'stopped': None, 'usage': {'used': 5, 'oldest_in_window': 'x'}, 'internal': 'hidden'})
    monkeypatch.setattr(source_review, 'source_request', forward)
    response = await call(app(UserRole.admin), 'POST', '/rentcast/price', {'limit': 5})
    assert response.status_code == 200
    forward.assert_awaited_once_with('POST', '/api/operations/rentcast/price', {'limit': 5})
    assert response.json() == {'requested': 5, 'priced': 4, 'no_data': 1, 'errors': 0, 'comps_saved': 60, 'stopped': None, 'usage': {'used': 5, 'hard_cap': 50, 'window_days': 31}}
