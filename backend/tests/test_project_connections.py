from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI

from api.routes import ingest, source_review
from core.redis import get_redis
from db.session import get_session
from models.enums import UserRole
from security.auth import get_current_active_user
from services import connection_status


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "nonce",
        "tenant",
        "receiver",
        "schema",
        "bob",
        "journal",
        "database",
        "source",
    ],
)
async def test_authenticated_round_trip_detects_wrong_instance_and_never_grants_contact(
    monkeypatch, fault
):
    monkeypatch.setenv("REI_SOURCE_TENANT_ID", "00000000-0000-0000-0000-000000000001")
    session = SimpleNamespace(
        rollback=AsyncMock(),
        execute=AsyncMock(
            side_effect=RuntimeError("secret-db-detail")
            if fault == "database"
            else None
        ),
    )

    async def forward(method, path):
        if fault == "source":
            raise RuntimeError("private-source-address")
        nonce = path.split("challenge=")[1]
        return {
            "schema_version": True if fault == "schema" else 1,
            "service": "rei-sophia",
            "challenge": str(uuid4()) if fault == "nonce" else nonce,
            "tenant_id": str(uuid4())
            if fault == "tenant"
            else connection_status.source_tenant(),
            "dashboard": {
                "status": "ok",
                "receiver_id": "wrong"
                if fault == "receiver"
                else connection_status.receiver_identity(),
            },
            "bob": "degraded" if fault == "bob" else "ok",
            "dashboard_journal": "unavailable" if fault == "journal" else "ok",
            "outbound_enabled": False,
            "background_jobs_enabled": False,
        }

    result = await connection_status.connection_status(session, forward)
    assert result["status"] == ("ok" if fault == "none" else "degraded")
    assert "secret-db-detail" not in str(
        result
    ) and "private-source-address" not in str(result)
    assert result["outbound_enabled"] is not True
    if fault == "receiver":
        assert {row["id"]: row["status"] for row in result["components"]}[
            "sophia_to_dashboard"
        ] == "wrong_receiver"


async def test_receiver_requires_service_authentication_and_nonce_and_hides_database_credentials(
    monkeypatch,
):
    monkeypatch.setenv("KARPATHYS_WEBHOOK_SECRET", "secret-for-events")
    app = FastAPI()
    app.include_router(ingest.router, prefix="/ingest")
    challenge = str(uuid4())
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as transport:
        assert (
            await transport.get("/ingest/connection?challenge=" + challenge)
        ).status_code == 401
        good = await transport.get(
            "/ingest/connection?challenge=" + challenge,
            headers={"X-Karpathys-Secret": "secret-for-events"},
        )
        bad = await transport.get(
            "/ingest/connection?challenge=bad",
            headers={"X-Karpathys-Secret": "secret-for-events"},
        )
    assert (
        good.json()["challenge"] == challenge and len(good.json()["receiver_id"]) == 64
    )
    assert bad.status_code == 422
    assert "postgresql" not in good.text and "secret-for-events" not in good.text


async def test_dashboard_probe_requires_operator_login(monkeypatch):
    app = FastAPI()
    app.include_router(source_review.router, prefix="/review")

    async def session():
        yield SimpleNamespace(execute=AsyncMock())

    app.dependency_overrides[get_session] = session
    app.dependency_overrides[get_redis] = lambda: None
    probe = AsyncMock(return_value={"status": "degraded"})
    monkeypatch.setattr(connection_status, "connection_status", probe)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as transport:
        assert (await transport.get("/review/connections")).status_code == 401
        app.dependency_overrides[get_current_active_user] = lambda: SimpleNamespace(
            id=uuid4(), role=UserRole.operator
        )
        assert (await transport.get("/review/connections")).json()[
            "status"
        ] == "degraded"
    assert probe.await_count == 1


def test_business_snapshot_rejects_wrong_configured_source_tenant(monkeypatch):
    from fastapi import HTTPException

    from services.business_evidence import validate_snapshot

    monkeypatch.setenv("REI_SOURCE_TENANT_ID", str(uuid4()))
    with pytest.raises(HTTPException) as failure:
        validate_snapshot(
            {
                "snapshot": {
                    "schema_version": 1,
                    "quote_authorized": False,
                    "offer_authorized": False,
                    "tenant_id": str(uuid4()),
                }
            }
        )
    assert failure.value.status_code == 409
