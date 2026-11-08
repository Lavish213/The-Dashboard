from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from api.routes import bob_insights
from models.enums import UserRole
from security.auth import get_current_active_user

DEAL = {
    'lead_id': '11111111-1111-1111-1111-111111111111', 'address': '1420 N El Dorado St', 'city': 'Stockton',
    'distress_score': 80, 'grade': 'A', 'readiness': 'HOT_BUY', 'evidence_confidence': 'verified',
    'economics_state': 'known', 'arv_point_cents': 46000000, 'asking_price_cents': 20000000,
    'purchase_limit_cents': 30200000, 'headroom_cents': 10200000, 'headroom_bps': 2217,
    'valuation_status': 'ready_advisory', 'valuation_verification': 'operator_attested', 'comparable_count': 5, 'blocked_count': 0,
    'lockout_class': None, 'next_action': 'prepare_offer_for_human_approval', 'graded_at': '2026-11-08T02:00:00Z',
    'owner_phone': '+12095550123', 'owner_name': 'never forwarded',
}
REPORT = {
    'schema_version': 1, 'generated_at': '2026-11-08T02:00:00Z', 'graded_leads': 2, 'blocked_leads': 1,
    'contactable_leads': 252, 'briefed_leads': 19, 'valuation_ready_leads': 2,
    'newest_grade_at': '2026-11-08T01:30:00Z', 'newest_grade_age_seconds': 1800, 'oldest_grade_age_seconds': 7200,
    'economics_unknown_leads': 0, 'by_readiness': {'HOT_BUY': 1, 'ARCHIVED': 1}, 'by_grade': {'A': 1, 'ungraded': 1},
    'by_evidence_confidence': {'verified': 1}, 'by_lockout_class': {'price_dependent': 1},
    'by_valuation_verification': {'operator_attested': 2}, 'deals': [DEAL],
    'authority': {'quote_authorized': False, 'offer_authorized': False, 'grading_basis': 'internal_screening_policy_not_an_appraisal_or_investment_guarantee'},
    'private_field': 'never forwarded',
}


def app(role=UserRole.operator):
    application = FastAPI()
    application.include_router(bob_insights.router, prefix='/test')
    application.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=uuid4(), role=role)
    return application


async def get(application, query=''):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=application), base_url='http://test') as client:
        return await client.get('/test/insights' + query)


def forward(monkeypatch, payload):
    mock = AsyncMock(return_value=payload)
    monkeypatch.setattr(bob_insights, 'source_request', mock)
    return mock


@pytest.mark.parametrize('role', [UserRole.operator, UserRole.reviewer, UserRole.admin])
async def test_insights_are_served_to_permitted_roles(role, monkeypatch):
    forward(monkeypatch, REPORT)
    response = await get(app(role))
    assert response.status_code == 200
    assert response.json()['graded_leads'] == 2


async def test_only_known_overview_fields_are_forwarded(monkeypatch):
    forward(monkeypatch, REPORT)
    body = (await get(app())).json()
    assert 'private_field' not in body
    assert body['by_readiness'] == {'HOT_BUY': 1, 'ARCHIVED': 1}


async def test_unexpected_deal_fields_are_never_forwarded(monkeypatch):
    forward(monkeypatch, REPORT)
    deal = (await get(app())).json()['deals'][0]
    assert 'owner_phone' not in deal
    assert 'owner_name' not in deal
    assert deal['headroom_cents'] == 10200000


async def test_the_response_always_states_no_authority(monkeypatch):
    forward(monkeypatch, REPORT)
    body = (await get(app())).json()
    assert body['quote_authorized'] is False
    assert body['offer_authorized'] is False
    assert 'not_an_appraisal_or_investment_guarantee' in body['grading_basis']


@pytest.mark.parametrize('authority', [
    {'quote_authorized': True, 'offer_authorized': False},
    {'quote_authorized': False, 'offer_authorized': True},
    {'quote_authorized': 'false', 'offer_authorized': 'false'},
    {'offer_authorized': False},
    None,
    'nope',
])
async def test_a_report_claiming_authority_is_withheld(authority, monkeypatch):
    forward(monkeypatch, {**REPORT, 'authority': authority})
    assert (await get(app())).status_code == 503


@pytest.mark.parametrize('version', [None, 0, 2, '1'])
async def test_an_unsupported_schema_version_is_withheld(version, monkeypatch):
    forward(monkeypatch, {**REPORT, 'schema_version': version})
    assert (await get(app())).status_code == 503


@pytest.mark.parametrize('deals', [None, {}, 'none', 7])
async def test_a_malformed_deal_list_is_withheld(deals, monkeypatch):
    forward(monkeypatch, {**REPORT, 'deals': deals})
    assert (await get(app())).status_code == 503


@pytest.mark.parametrize('bad', [
    {'readiness': 'APPROVED_TO_OFFER'},
    {'readiness': None},
    {'lead_id': None},
    {'lead_id': 12345},
])
async def test_deals_with_an_unknown_readiness_or_identity_are_dropped(bad, monkeypatch):
    forward(monkeypatch, {**REPORT, 'deals': [{**DEAL, **bad}]})
    response = await get(app())
    assert response.status_code == 200
    assert response.json()['deals'] == []


async def test_non_object_deal_rows_are_dropped_without_failing_the_report(monkeypatch):
    forward(monkeypatch, {**REPORT, 'deals': ['nope', None, 7, DEAL]})
    body = (await get(app())).json()
    assert len(body['deals']) == 1


@pytest.mark.parametrize('query,expected', [('?limit=0', 422), ('?limit=101', 422), ('?limit=-5', 422), ('?limit=abc', 422), ('?limit=1', 200), ('?limit=100', 200)])
async def test_the_limit_is_bounded(query, expected, monkeypatch):
    forward(monkeypatch, REPORT)
    assert (await get(app(), query)).status_code == expected


async def test_the_limit_is_passed_through_to_the_source(monkeypatch):
    mock = forward(monkeypatch, REPORT)
    await get(app(), '?limit=7')
    assert mock.await_args.args[1] == '/api/bob/insights?limit=7'


PRODUCER_DEAL_FIELDS = (
    'lead_id', 'address', 'city', 'distress_score', 'grade', 'readiness', 'evidence_confidence',
    'economics_state', 'arv_point_cents', 'asking_price_cents', 'purchase_limit_cents',
    'headroom_cents', 'headroom_bps', 'valuation_status', 'valuation_verification', 'comparable_count', 'blocked_count',
    'lockout_class', 'next_action', 'graded_at',
)
PRODUCER_OVERVIEW_FIELDS = (
    'schema_version', 'generated_at', 'graded_leads', 'contactable_leads', 'briefed_leads',
    'valuation_ready_leads', 'newest_grade_at', 'newest_grade_age_seconds', 'oldest_grade_age_seconds',
    'blocked_leads', 'economics_unknown_leads',
    'by_readiness', 'by_grade', 'by_evidence_confidence', 'by_lockout_class', 'by_valuation_verification',
)


async def test_no_field_bob_sends_is_silently_dropped(monkeypatch):
    forward(monkeypatch, REPORT)
    body = (await get(app())).json()
    missing_overview = [field for field in PRODUCER_OVERVIEW_FIELDS if field not in body]
    missing_deal = [field for field in PRODUCER_DEAL_FIELDS if field not in body['deals'][0]]
    assert not missing_overview, f'overview fields dropped: {missing_overview}'
    assert not missing_deal, f'deal fields dropped: {missing_deal}'


def test_the_whitelists_match_the_producer_contract():
    assert set(bob_insights.DEAL_FIELDS) == set(PRODUCER_DEAL_FIELDS)
    assert set(bob_insights.OVERVIEW_FIELDS) == set(PRODUCER_OVERVIEW_FIELDS)


async def test_the_funnel_denominator_reaches_the_client(monkeypatch):
    forward(monkeypatch, REPORT)
    body = (await get(app())).json()
    assert body['contactable_leads'] == 252
    assert body['briefed_leads'] == 19
    assert body['valuation_ready_leads'] == 2


async def test_grade_freshness_reaches_the_client(monkeypatch):
    forward(monkeypatch, REPORT)
    body = (await get(app())).json()
    assert body['newest_grade_age_seconds'] == 1800
    assert body['newest_grade_at'] == '2026-11-08T01:30:00Z'


async def test_the_provenance_class_reaches_the_client(monkeypatch):
    forward(monkeypatch, REPORT)
    body = (await get(app())).json()
    assert body['deals'][0]['valuation_verification'] == 'operator_attested'
    assert body['by_valuation_verification'] == {'operator_attested': 2}
