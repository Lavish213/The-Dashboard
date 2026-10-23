from copy import deepcopy

import pytest

from services.delivery_evidence import validate_delivery_overview


def receipt():
    return {'schema_version': 1, 'tenant_id': '00000000-0000-0000-0000-000000000001', 'journal': {'pending': 1, 'received': 5, 'oldest_pending_seconds': 10}, 'messages': [{'intent_id': 'a' * 64, 'lead_id': None, 'channel': 'email', 'delivery_status': 'conflicting_receipts', 'opened': True, 'clicked': False, 'suppressed': True, 'recipient': 'private@example.invalid', 'payload': 'private'}]}


def test_delivery_read_model_redacts_recipient_and_raw_payload(monkeypatch):
    monkeypatch.delenv('REI_SOURCE_TENANT_ID', raising=False)
    result = validate_delivery_overview(receipt())
    assert result['messages'][0]['delivery_status'] == 'conflicting_receipts'
    assert 'private' not in str(result)


@pytest.mark.parametrize('fault', ['tenant', 'schema', 'journal', 'counter', 'status', 'flag', 'identity', 'bound'])
def test_malformed_or_wrong_tenant_delivery_never_shows_verified_data(monkeypatch, fault):
    monkeypatch.delenv('REI_SOURCE_TENANT_ID', raising=False)
    data = deepcopy(receipt())
    if fault == 'tenant':
        data['tenant_id'] = '00000000-0000-0000-0000-000000000002'
    if fault == 'schema':
        data['schema_version'] = True
    if fault == 'journal':
        data['journal'] = []
    if fault == 'counter':
        data['journal']['pending'] = True
    if fault == 'status':
        data['messages'][0]['delivery_status'] = 'accepted_offer'
    if fault == 'flag':
        data['messages'][0]['opened'] = 1
    if fault == 'identity':
        data['messages'][0]['intent_id'] = 'not-an-id'
    if fault == 'bound':
        data['messages'] *= 101
    with pytest.raises((ValueError, TypeError)):
        validate_delivery_overview(data)


def test_inventory_includes_no_callback_and_uncertain_submissions(monkeypatch):
    monkeypatch.delenv('REI_SOURCE_TENANT_ID', raising=False)
    data = receipt()
    data['inventory'] = {'accepted': 5, 'uncertain_submission': 2, 'pending_projection': 1, 'recipient': 'private'}
    result = validate_delivery_overview(data)
    assert result['inventory'] == {'accepted': 5, 'uncertain_submission': 2, 'pending_projection': 1}
    assert 'private' not in str(result)
    del data['inventory']
    assert validate_delivery_overview(data)['inventory'] is None


@pytest.mark.parametrize('value', [True, -1, '5', [], {}])
def test_invalid_inventory_cannot_be_presented_as_verified(value, monkeypatch):
    monkeypatch.delenv('REI_SOURCE_TENANT_ID', raising=False)
    data = receipt()
    data['inventory'] = {'accepted': value, 'uncertain_submission': 0, 'pending_projection': 0}
    with pytest.raises(ValueError):
        validate_delivery_overview(data)
