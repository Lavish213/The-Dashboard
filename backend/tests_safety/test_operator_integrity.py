from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from api.routes import leads, notifications, settings
from db.session import get_session
from models.enums import UserRole
from realtime.subscriptions import channel_allowed
from security.auth import get_current_active_user

OWN = UUID("00000000-0000-4000-8000-000000000001")
OTHER = UUID("00000000-0000-4000-8000-000000000002")


def forbidden_database():
    raise AssertionError("Rejected operations must not access the database")


def client_for(router, role):
    app = FastAPI()
    app.include_router(router, prefix="/test")
    app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=OWN, role=role)
    app.dependency_overrides[get_session] = forbidden_database
    return TestClient(app)


@pytest.mark.parametrize("role", [UserRole.operator, UserRole.reviewer])
@pytest.mark.parametrize("method,path", [
    ("GET", ""), ("GET", "/unread-count"), ("POST", "/read-all"),
    ("POST", f"/{OTHER}/read"),
])
def test_cross_account_notifications_rejected_before_database(role, method, path):
    with client_for(notifications.router, role) as client:
        assert client.request(method, f"/test{path}?user_id={OTHER}").status_code == 403


@pytest.mark.parametrize("path,method,body", [
    (f"/{OTHER}/status?status=qualified", "PATCH", None),
    (f"/{OTHER}/notes", "POST", {"content": "Forbidden"}),
    (f"/{OTHER}/notes", "PATCH", {"notes": "Forbidden"}),
    (f"/{OTHER}/followup", "PATCH", {"follow_up_at": None}),
])
def test_read_only_role_cannot_mutate_leads(path, method, body):
    with client_for(leads.router, UserRole.reviewer) as client:
        assert client.request(method, "/test" + path, json=body).status_code == 403


@pytest.mark.parametrize("role", [UserRole.operator, UserRole.reviewer])
def test_team_roster_is_admin_only(role):
    with client_for(settings.router, role) as client:
        assert client.get("/test/team").status_code == 403


@pytest.mark.parametrize("value", ["bad date", "2000-01-01T10:00:00Z", "2099-01-01T10:00:00", True, 1234])
def test_followup_rejects_invalid_past_and_naive_dates(value):
    with pytest.raises(ValidationError):
        leads.FollowupUpdate(follow_up_at=value)


def test_followup_accepts_timezone_and_explicit_cancellation():
    future = datetime.now(UTC) + timedelta(days=2)
    assert leads.FollowupUpdate(follow_up_at=future).follow_up_at == future
    assert leads.FollowupUpdate(follow_up_at=None).follow_up_at is None
    with pytest.raises(ValidationError):
        leads.FollowupUpdate()


@pytest.mark.parametrize("role", ["operator", "reviewer"])
def test_notification_channels_cannot_cross_accounts(role):
    assert channel_allowed(f"user:{OWN}", role, str(OWN))
    assert not channel_allowed(f"user:{OTHER}", role, str(OWN))
    assert not channel_allowed(f"user:{OWN}", role)
    assert not channel_allowed(f"lead:{OWN}", "unrecognized", str(OWN))


def test_configuration_is_server_reported_without_secrets():
    with client_for(settings.router, UserRole.operator) as client:
        response = client.get("/test")
    assert response.status_code == 200
    data = response.json()
    assert data["security"]["access_token_minutes"] == settings.settings.access_token_expire_minutes
    assert data["source"] == "dashboard_server"
    assert not data["voice_configuration"]["available"]
    assert "secret_key" not in data and "database_url" not in data
