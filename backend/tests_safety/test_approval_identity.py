from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.routes import approvals
from db.session import get_session
from models.enums import ApprovalStatus, ApprovalType, RiskLevel, UserRole
from schemas.approval import ApprovalCreate
from security.auth import get_current_active_user


@pytest.mark.parametrize('role', [UserRole.operator])
def test_operator_cannot_resolve_approval_before_database(role):
    app = FastAPI()
    app.include_router(approvals.router)
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=uuid4(), role=role)
    def forbidden():
        raise AssertionError('Forbidden actor must not reach database')
    app.dependency_overrides[get_session] = forbidden
    with TestClient(app) as client:
        response = client.post(f'/{uuid4()}/resolve', json={'approval_status': 'approved'})
    assert response.status_code == 403


@pytest.mark.parametrize('operation', ['request', 'resolve'])
def test_authenticated_actor_cannot_spoof_another_approver(operation, monkeypatch):
    app = FastAPI()
    app.include_router(approvals.router)
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=uuid4(), role=UserRole.admin)
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    def forbidden(*args):
        raise AssertionError('Spoofed actor must not reach approval engine')
    monkeypatch.setattr(approvals, 'ApprovalEngine', forbidden)
    path = '/request' if operation == 'request' else f'/{uuid4()}/resolve'
    body = {'workflow_id': str(uuid4()), 'approval_type': 'offer', 'requested_by': str(uuid4())} if operation == 'request' else {'approval_status': 'approved', 'resolved_by': str(uuid4())}
    with TestClient(app) as client:
        response = client.post(path, json=body)
    assert response.status_code == 403


@pytest.mark.parametrize('expiry', ['2020-01-01T00:00:00Z', '2099-01-01T00:00:00', 'not-a-date'])
def test_approval_expiry_rejects_past_naive_or_invalid(expiry):
    with pytest.raises(ValidationError):
        ApprovalCreate(workflow_id=uuid4(), approval_type='offer', expires_at=expiry)


@pytest.mark.parametrize('actor', [None, 'same'])
def test_null_or_matching_actor_resolves_as_authenticated_reviewer(actor, monkeypatch):
    identity = SimpleNamespace(id=uuid4(), role=UserRole.reviewer)
    approval_id, workflow_id = uuid4(), uuid4()
    result = SimpleNamespace(id=approval_id, workflow_id=workflow_id, approval_type=ApprovalType.offer, approval_status=ApprovalStatus.approved, requested_by=None, resolved_by=identity.id, expires_at=datetime.now(UTC)+timedelta(hours=1), risk_level=RiskLevel.low, resolution_notes=None, created_at=datetime.now(UTC), updated_at=datetime.now(UTC))
    engine = SimpleNamespace(resolve=AsyncMock(return_value=result))
    monkeypatch.setattr(approvals, 'ApprovalEngine', lambda session: engine)
    app = FastAPI()
    app.include_router(approvals.router)
    app.dependency_overrides[get_current_active_user] = lambda: identity
    app.dependency_overrides[get_session] = lambda: AsyncMock()
    with TestClient(app) as client:
        response = client.post(f'/{approval_id}/resolve', json={'approval_status': 'approved', 'resolved_by': str(identity.id) if actor else None})
    assert response.status_code == 200
    assert response.json()['resolved_by'] == str(identity.id)
    assert engine.resolve.call_args.kwargs['resolved_by'] == identity.id
    assert engine.resolve.call_args.kwargs['commit_before_publish'] is True
