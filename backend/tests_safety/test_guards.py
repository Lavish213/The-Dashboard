import asyncio
from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from api.routes import property_search
from api.routes.handoff import router
from db.session import get_session
from models.enums import UserRole
from security.auth import get_current_active_user
from security.webhooks import verify_karpathys_secret
from testing.database import validate_disposable_database


def test_unconfigured_webhook_fails_closed(monkeypatch):
    monkeypatch.delenv("KARPATHYS_WEBHOOK_SECRET", raising=False)
    with pytest.raises(HTTPException) as error:
        verify_karpathys_secret("")
    assert error.value.status_code == 503


@pytest.mark.parametrize("value", ["", "wrong", "secret ", "秘密"])
def test_wrong_secret_is_denied(monkeypatch, value):
    monkeypatch.setenv("KARPATHYS_WEBHOOK_SECRET", "secret")
    with pytest.raises(HTTPException) as error:
        verify_karpathys_secret(value)
    assert error.value.status_code == 401


def test_exact_secret_is_accepted(monkeypatch):
    monkeypatch.setenv("KARPATHYS_WEBHOOK_SECRET", "secret")
    assert verify_karpathys_secret("secret") is None


def test_unconfigured_property_search_is_unavailable(monkeypatch):
    monkeypatch.setattr(property_search, "_BATCHDATA_KEY", "")
    with pytest.raises(HTTPException) as error:
        asyncio.run(property_search.search_properties("123 Main Street", None))
    assert error.value.status_code == 503


@pytest.mark.parametrize("response,expected", [
    (httpx.Response(200, json={"results": {"properties": []}}), []),
    (httpx.Response(500), 502), (httpx.Response(200, content=b"bad json"), 502),
])
def test_provider_failures_are_not_fake_property_records(monkeypatch, response, expected):
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            return response
    monkeypatch.setattr(property_search, "_BATCHDATA_KEY", "synthetic")
    monkeypatch.setattr(property_search.httpx, "AsyncClient", Client)
    if expected == []:
        assert asyncio.run(property_search.search_properties("123 Main Street", None)) == []
    else:
        with pytest.raises(HTTPException) as error:
            asyncio.run(property_search.search_properties("123 Main Street", None))
        assert error.value.status_code == expected


@pytest.mark.parametrize("action,field", [("accept", "accepted_by"), ("reject", "rejected_by"), ("initiate", "operator_user_id")])
@pytest.mark.parametrize("role", [UserRole.operator, UserRole.reviewer])
def test_handoff_identity_and_read_only_role_are_enforced(action, field, role):
    application = FastAPI()
    application.include_router(router, prefix="/api")
    own = UUID("00000000-0000-0000-0000-000000000001")
    other = "00000000-0000-0000-0000-000000000002"
    application.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(id=own, role=role)
    async def no_database():
        yield None
    application.dependency_overrides[get_session] = no_database
    body = {field: other if role == UserRole.operator else str(own), "reason": "synthetic"}
    if action == "initiate":
        body.update(session_id=other, turn_id=other)
        path = "/api/handoff/initiate"
    else:
        path = f"/api/handoff/{other}/{action}"
    assert TestClient(application).post(path, json=body).status_code == 403


@pytest.mark.parametrize("dsn", ["", "postgresql+asyncpg://postgres:postgres@localhost/production",
    "postgresql+asyncpg://postgres:postgres@db.example.invalid/karpathys_test", "sqlite:///karpathys_test"])
def test_schema_reset_rejects_non_disposable_destinations(dsn):
    with pytest.raises(pytest.UsageError):
        validate_disposable_database(dsn)
