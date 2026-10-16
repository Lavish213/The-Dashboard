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
