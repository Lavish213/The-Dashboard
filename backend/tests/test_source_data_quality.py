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
