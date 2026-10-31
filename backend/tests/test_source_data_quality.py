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


MAIL = {'schema_version': 1, 'priced_only': True, 'count': 2, 'rows': [
    {'lead_id': 'l1', 'owner_name': '=HYPERLINK("x")', 'mailing_address': '1 Mail Rd\nApt 2', 'mailing_city': 'Lodi', 'mailing_state': 'CA', 'mailing_zip': '95240',
     'property_address': '10 Main St', 'property_city': 'Stockton', 'property_zip': '95205', 'value_cents': 45000000, 'mao_cents': 29000000,
     'value_source': 'rentcast_avm', 'distress_type': 'vacant', 'distress_score': 70},
    {'lead_id': 'l2', 'owner_name': 'Bo', 'value_cents': None, 'mao_cents': True},
]}


async def test_mail_list_is_admin_only(monkeypatch):
    forward = AsyncMock(return_value=MAIL)
    monkeypatch.setattr(source_review, 'source_request', forward)
    for role in (UserRole.operator, UserRole.reviewer):
        assert (await call(app(role), 'GET', '/mail-list.csv')).status_code == 403
    forward.assert_not_awaited()


async def test_mail_list_csv_is_safe_and_in_dollars(monkeypatch):
    forward = AsyncMock(return_value=MAIL)
    monkeypatch.setattr(source_review, 'source_request', forward)
    response = await call(app(UserRole.admin), 'GET', '/mail-list.csv?priced_only=false')
    assert response.status_code == 200
    forward.assert_awaited_once_with('GET', '/api/operations/mail-list?priced_only=false')
    assert response.headers['content-type'].startswith('text/csv')
    assert 'mail-list-all.csv' in response.headers['content-disposition']
    lines = response.text.splitlines()
    assert lines[0].startswith('owner_name,mailing_address')
    assert lines[1].startswith('"\'=HYPERLINK(""x"")",1 Mail Rd Apt 2,Lodi')
    assert ',450000,290000,rentcast_avm,' in lines[1]
    assert lines[2].startswith('Bo,') and 'True' not in lines[2] and len(lines) == 3
    assert 'lead_id' not in lines[0]


async def test_mail_list_bad_schema(monkeypatch):
    monkeypatch.setattr(source_review, 'source_request', AsyncMock(return_value={'schema_version': 2, 'rows': []}))
    assert (await call(app(UserRole.admin), 'GET', '/mail-list.csv')).status_code == 503


REAL_CLIENT = httpx.AsyncClient


class Upstream:
    def __init__(self, status=200, body=None):
        self.status, self.body, self.requests = status, body, []

    def handler(self, request):
        self.requests.append(request)
        return httpx.Response(self.status, json=self.body if self.body is not None else {'parsed': 3, 'upserted': 3, 'scored': 3, 'leads_created': 2, 'skipped_score': 0, 'errors': 0, 'extra': 1})


async def upload(application, content, monkeypatch, upstream):
    monkeypatch.setattr(source_review, 'destination', lambda: ('https://sophia.test', 'k' * 40, None))
    real = REAL_CLIENT

    def fake(*args, **kwargs):
        kwargs.pop('transport', None)
        return real(*args, transport=httpx.MockTransport(upstream.handler), **kwargs)
    monkeypatch.setattr(source_review.httpx, 'AsyncClient', fake)
    async with real(transport=httpx.ASGITransport(app=application), base_url='http://test') as client:
        return await client.post('/test/import-csv', content=content, headers={'content-type': 'text/csv'})


async def test_import_is_admin_only(monkeypatch):
    upstream = Upstream()
    for role in (UserRole.operator, UserRole.reviewer):
        assert (await upload(app(role), b'a,b\n', monkeypatch, upstream)).status_code == 403
    assert upstream.requests == []


async def test_import_forwards_file_with_secret(monkeypatch):
    upstream = Upstream()
    response = await upload(app(UserRole.admin), b'Address\n1 A St\n', monkeypatch, upstream)
    assert response.status_code == 200
    assert response.json() == {'parsed': 3, 'upserted': 3, 'scored': 3, 'leads_created': 2, 'skipped_score': 0, 'errors': 0}
    sent = upstream.requests[0]
    assert str(sent.url) == 'https://sophia.test/api/operations/import-csv'
    assert sent.headers['x-source-command-secret'] == 'k' * 40
    assert b'1 A St' in sent.content and b'filename="import.csv"' in sent.content


@pytest.mark.parametrize('content', [b'', b'x' * (10 * 1024 * 1024 + 1)])
async def test_import_rejects_bad_size(monkeypatch, content):
    upstream = Upstream()
    assert (await upload(app(UserRole.admin), content, monkeypatch, upstream)).status_code == 400
    assert upstream.requests == []


@pytest.mark.parametrize('status,body,expected', [(400, {}, 400), (500, {}, 503), (200, {'parsed': 'x'}, 503)])
async def test_import_upstream_failures(monkeypatch, status, body, expected):
    assert (await upload(app(UserRole.admin), b'a\n', monkeypatch, Upstream(status, body))).status_code == expected
