import hashlib
import json
from datetime import UTC, datetime
from urllib.parse import urlsplit
from uuid import UUID, uuid4

from sqlalchemy import text

from config.settings import settings


def source_tenant():
    import os

    return str(
        UUID(
            os.environ.get("REI_SOURCE_TENANT_ID")
            or "00000000-0000-0000-0000-000000000001"
        )
    )


def receiver_identity():
    parsed = urlsplit(settings.database_url)
    if (
        not parsed.hostname
        or not parsed.path
        or not parsed.scheme.startswith("postgresql")
    ):
        raise ValueError("Dashboard database identity unavailable")
    identity = [
        parsed.hostname.lower(),
        parsed.port or 5432,
        parsed.path,
        source_tenant(),
    ]
    return hashlib.sha256(
        json.dumps(identity, separators=(",", ":")).encode()
    ).hexdigest()


async def connection_status(session, source_request):
    checked = datetime.now(UTC).isoformat()
    components = {
        "dashboard_database": "unavailable",
        "dashboard_to_sophia": "unavailable",
        "sophia_to_dashboard": "unavailable",
        "bob_shared_database_and_worker": "unavailable",
        "sophia_dashboard_journal": "unavailable",
    }
    try:
        await session.execute(text("SELECT 1"))
        components["dashboard_database"] = "ok"
    except Exception:
        try:
            await session.rollback()
        except Exception:
            components["dashboard_database"] = "unavailable"
    outbound = background = None
    challenge = str(uuid4())
    try:
        data = await source_request(
            "GET", "/api/operations/integration?challenge=" + challenge
        )
        if (
            type(data.get("schema_version")) is not int
            or data.get("schema_version") != 1
            or data.get("service") != "rei-sophia"
            or data.get("challenge") != challenge
            or data.get("tenant_id") != source_tenant()
            or type(data.get("background_jobs_enabled")) is not bool
            or type(data.get("outbound_enabled")) is not bool
        ):
            raise ValueError("Unbound source connection receipt")
        components["dashboard_to_sophia"] = "ok"
        receiver = data.get("dashboard") or {}
        components["sophia_to_dashboard"] = (
            "ok"
            if receiver.get("status") == "ok"
            and receiver.get("receiver_id") == receiver_identity()
            else "wrong_receiver"
            if receiver.get("status") == "ok"
            else "unavailable"
        )
        components["bob_shared_database_and_worker"] = (
            "ok" if data.get("bob") == "ok" else "degraded"
        )
        components["sophia_dashboard_journal"] = (
            "ok" if data.get("dashboard_journal") == "ok" else "degraded"
        )
        outbound, background = data["outbound_enabled"], data["background_jobs_enabled"]
    except Exception:
        if components["dashboard_to_sophia"] != "ok":
            components["dashboard_to_sophia"] = "unconfirmed"
    return {
        "schema_version": 1,
        "status": "ok"
        if all(value == "ok" for value in components.values())
        else "degraded",
        "checked_at": checked,
        "components": [
            {"id": name, "status": value} for name, value in components.items()
        ],
        "outbound_enabled": outbound,
        "background_jobs_enabled": background,
        "verification_scope": "authenticated_round_trip_and_reported_health_not_live_provider_delivery",
    }
