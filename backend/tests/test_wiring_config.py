import json
from copy import deepcopy

import pytest

from services.wiring_config import verify_wiring


def configuration():
    tenant = "00000000-0000-0000-0000-000000000001"
    bob = {
        "SUPABASE_URL": "https://shared.supabase.co",
        "SUPABASE_SERVICE_KEY": "private-data-key",
        "BOB_TENANT_ID": tenant,
        "REI_COMMAND_URL": "https://sophia.example.invalid",
        "KARPATHYS_WEBHOOK_SECRET": "e" * 40,
    }
    rei = {
        "SUPABASE_URL": bob["SUPABASE_URL"],
        "SUPABASE_SERVICE_KEY": "different-permitted-service-key",
        "TENANT_ID": tenant,
        "KARPATHYS_URL": "https://dashboard.example.invalid",
        "KARPATHYS_WEBHOOK_SECRET": "e" * 40,
        "SOURCE_COMMAND_SECRET": "c" * 40,
    }
    for key in (
        "VOICE_FACT_OUTBOX_PATH",
        "KARPATHYS_OUTBOX_PATH",
        "CONTACT_SUPPRESSION_PATH",
        "COMMUNICATION_JOURNAL_PATH",
        "WORKFLOW_JOURNAL_PATH",
    ):
        rei[key] = "/data/" + key.lower() + ".sqlite3"
    dashboard = {
        "REI_SOURCE_TENANT_ID": tenant,
        "REI_COMMAND_URL": "https://sophia.example.invalid",
        "KARPATHYS_WEBHOOK_SECRET": "e" * 40,
        "SOURCE_COMMAND_SECRET": "c" * 40,
        "NEXT_PUBLIC_API_URL": "https://dashboard.example.invalid",
        "DASHBOARD_FRONTEND_ORIGIN": "https://frontend.example.invalid",
        "CORS_ORIGINS": '["https://frontend.example.invalid"]',
        "NEXT_PUBLIC_WS_URL": "wss://dashboard.example.invalid",
    }
    return bob, rei, dashboard


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "database",
        "tenant",
        "events",
        "commands",
        "event_url",
        "self",
        "path",
        "relative",
        "missing",
        "browser",
        "websocket",
        "missing_proxy",
    ],
)
def test_configuration_alignment_fails_closed_without_printing_values(fault):
    configs = configuration()
    bob, rei, dashboard = configs
    if fault == "database":
        bob["SUPABASE_URL"] = "https://wrong.supabase.co"
    if fault == "tenant":
        bob["BOB_TENANT_ID"] = "bad"
    if fault == "events":
        rei["KARPATHYS_WEBHOOK_SECRET"] = "wrong" * 10
    if fault == "commands":
        dashboard["SOURCE_COMMAND_SECRET"] = ""
    if fault == "event_url":
        bob["BOB_EVENT_URL"] = (
            "https://dashboard.example.invalid/api/ingest/bob/brief-created"
        )
    if fault == "self":
        rei["KARPATHYS_URL"] = dashboard["REI_COMMAND_URL"]
    if fault == "path":
        dashboard["REI_COMMAND_URL"] += "/api"
    if fault == "relative":
        rei["KARPATHYS_OUTBOX_PATH"] = "./tmp/path"
    if fault == "missing":
        bob.clear()
    if fault == "browser":
        dashboard["NEXT_PUBLIC_API_URL"] = "https://wrong.example.invalid"
    if fault == "websocket":
        dashboard["NEXT_PUBLIC_WS_URL"] = ""
    if fault == "missing_proxy":
        dashboard["NEXT_PUBLIC_API_URL"] = ""
    saved = deepcopy(configs)
    result = verify_wiring(*configs)
    assert configs == saved
    assert result["status"] == (
        "configuration_consistent" if fault == "none" else "blocked"
    )
    serialized = json.dumps(result)
    for secret in ("private-data-key", "e" * 40, "c" * 40, "shared.supabase.co"):
        assert secret not in serialized


@pytest.mark.parametrize(
    "allowed",
    [
        "",
        '["http://localhost:3000"]',
        '["https://frontend.example.invalid/"]',
        '["https://frontend.example.invalid.evil.test"]',
        '["*"]',
        '"https://frontend.example.invalid"',
        '{"https://frontend.example.invalid": true}',
        '["https://frontend.example.invalid", null]',
        "null",
        42,
    ],
)
def test_split_origin_blocks_cors_that_cannot_accept_browser(allowed):
    bob, rei, dashboard = configuration()
    dashboard["CORS_ORIGINS"] = allowed
    result = verify_wiring(bob, rei, dashboard)
    assert result["status"] == "blocked"
    assert "browser_frontend_origin_not_allowed_by_cors" in result["issues"]
    assert "frontend.example.invalid" not in json.dumps(result)


@pytest.mark.parametrize(
    "allowed",
    [
        '["https://frontend.example.invalid"]',
        "https://other.example.invalid, https://frontend.example.invalid",
        ["https://frontend.example.invalid"],
    ],
)
def test_split_origin_accepts_explicit_frontend_cors_membership(allowed):
    bob, rei, dashboard = configuration()
    dashboard["CORS_ORIGINS"] = allowed
    assert verify_wiring(bob, rei, dashboard)["status"] == "configuration_consistent"


@pytest.mark.parametrize("frontend", ["", "*", "https://frontend.example.invalid/path"])
def test_split_origin_requires_known_frontend_origin(frontend):
    bob, rei, dashboard = configuration()
    dashboard["DASHBOARD_FRONTEND_ORIGIN"] = frontend
    result = verify_wiring(bob, rei, dashboard)
    assert result["status"] == "blocked"
    assert "DASHBOARD_FRONTEND_ORIGIN_missing_or_invalid" in result["issues"]


def test_same_origin_proxy_does_not_require_cors_configuration():
    bob, rei, dashboard = configuration()
    dashboard["NEXT_PUBLIC_API_URL"] = ""
    dashboard["NEXT_PUBLIC_WS_URL"] = ""
    dashboard["DASHBOARD_SAME_ORIGIN_PROXY"] = "true"
    dashboard.pop("DASHBOARD_FRONTEND_ORIGIN")
    dashboard.pop("CORS_ORIGINS")
    assert verify_wiring(bob, rei, dashboard)["status"] == "configuration_consistent"


def test_explicit_same_origin_api_does_not_require_cors():
    bob, rei, dashboard = configuration()
    dashboard["DASHBOARD_FRONTEND_ORIGIN"] = rei["KARPATHYS_URL"]
    dashboard.pop("CORS_ORIGINS")
    assert verify_wiring(bob, rei, dashboard)["status"] == "configuration_consistent"
