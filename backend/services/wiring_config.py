import hmac
from pathlib import PurePosixPath
from urllib.parse import urlsplit
from uuid import UUID


def origin(value, allow_loopback=False):
    parsed = urlsplit(value)
    if (
        not parsed.hostname
        or parsed.username
        or parsed.password
        or parsed.query
        or parsed.fragment
        or parsed.path not in {"", "/"}
        or parsed.scheme not in {"https", "http"}
    ):
        raise ValueError("Valid origin required")
    if parsed.scheme == "http" and not (
        allow_loopback and parsed.hostname in {"localhost", "127.0.0.1", "::1"}
    ):
        raise ValueError("HTTPS required")
    port = parsed.port
    if port is not None and not 1 <= port <= 65535:
        raise ValueError("Invalid port")
    host = (
        "[" + parsed.hostname.lower() + "]"
        if ":" in parsed.hostname
        else parsed.hostname.lower()
    )
    standard = port is None or port == (443 if parsed.scheme == "https" else 80)
    return parsed.scheme + "://" + host + ("" if standard else ":" + str(port))


def verify_wiring(bob, rei, dashboard, allow_loopback=False):
    issues = []

    def check(condition, code):
        if not condition:
            issues.append(code)

    def endpoint(config, key):
        try:
            return origin(config.get(key, ""), allow_loopback)
        except (ValueError, TypeError, AttributeError):
            issues.append(key + "_missing_or_invalid")
            return None

    shared_bob, shared_rei = (
        endpoint(bob, "SUPABASE_URL"),
        endpoint(rei, "SUPABASE_URL"),
    )
    check(
        shared_bob is not None and shared_bob == shared_rei,
        "bob_sophia_database_project_mismatch",
    )
    for name, config in [("bob", bob), ("sophia", rei)]:
        value = config.get("SUPABASE_SERVICE_KEY", "")
        check(
            bool(value)
            and not any(
                word in value.lower()
                for word in ("placeholder", "your-", "your_", "example")
            ),
            name + "_database_credential_missing",
        )
    tenants = []
    for config, key in [
        (bob, "BOB_TENANT_ID"),
        (rei, "TENANT_ID"),
        (dashboard, "REI_SOURCE_TENANT_ID"),
    ]:
        try:
            tenants.append(str(UUID(config.get(key, ""))))
        except (ValueError, TypeError, AttributeError):
            issues.append(key + "_missing_or_invalid")
    check(len(tenants) == 3 and len(set(tenants)) == 1, "tenant_mismatch")
    tokens = [
        config.get("KARPATHYS_WEBHOOK_SECRET", "") for config in (bob, rei, dashboard)
    ]
    check(
        all(isinstance(value, str) and len(value) >= 32 for value in tokens)
        and all(
            hmac.compare_digest(tokens[0].encode(), value.encode()) for value in tokens
        ),
        "event_authentication_mismatch_or_missing",
    )
    commands = [config.get("SOURCE_COMMAND_SECRET", "") for config in (rei, dashboard)]
    check(
        all(isinstance(value, str) and len(value) >= 32 for value in commands)
        and hmac.compare_digest(commands[0].encode(), commands[1].encode()),
        "command_authentication_mismatch_or_missing",
    )
    source = endpoint(dashboard, "REI_COMMAND_URL")
    receiver = endpoint(rei, "KARPATHYS_URL")
    check(
        receiver is not None and receiver != source,
        "sophia_dashboard_destination_is_missing_or_self",
    )
    browser = dashboard.get("NEXT_PUBLIC_API_URL", "")
    if browser:
        check(
            endpoint(dashboard, "NEXT_PUBLIC_API_URL") == receiver,
            "browser_api_destination_mismatch",
        )
    else:
        check(
            dashboard.get("DASHBOARD_SAME_ORIGIN_PROXY", "").lower() == "true",
            "browser_requires_api_origin_or_verified_same_origin_proxy",
        )
    websocket = dashboard.get("NEXT_PUBLIC_WS_URL", "")
    if websocket:
        try:
            parsed = urlsplit(websocket)
            if parsed.scheme not in {"ws", "wss"}:
                raise ValueError("WebSocket origin required")
            translated = parsed._replace(
                scheme="https" if parsed.scheme == "wss" else "http"
            ).geturl()
            check(
                origin(translated, allow_loopback) == receiver,
                "browser_websocket_destination_mismatch",
            )
        except (ValueError, TypeError, AttributeError):
            issues.append("browser_websocket_destination_missing_or_invalid")
    else:
        check(not browser, "split_origin_browser_requires_websocket_origin")
    configured = bob.get("BOB_EVENT_URL") or (
        (bob.get("REI_COMMAND_URL") or "").rstrip("/") + "/api/ingest/bob/brief-created"
        if bob.get("REI_COMMAND_URL")
        else ""
    )
    try:
        parsed = urlsplit(configured)
        base = origin(parsed._replace(path="").geturl(), allow_loopback)
        check(
            base == source and parsed.path == "/api/ingest/bob/brief-created",
            "bob_event_destination_mismatch",
        )
    except (ValueError, TypeError, AttributeError):
        issues.append("bob_event_destination_missing_or_invalid")
    for key in (
        "VOICE_FACT_OUTBOX_PATH",
        "KARPATHYS_OUTBOX_PATH",
        "CONTACT_SUPPRESSION_PATH",
        "COMMUNICATION_JOURNAL_PATH",
        "WORKFLOW_JOURNAL_PATH",
    ):
        path = PurePosixPath(rei.get(key) or ".")
        check(
            path.is_absolute() and ".." not in path.parts,
            key + "_requires_private_persistent_path",
        )
    return {
        "schema_version": 1,
        "status": "configuration_consistent" if not issues else "blocked",
        "issues": sorted(set(issues)),
        "verification_scope": "configuration_only_no_network_database_provider_or_volume_proof",
        "outbound_enabled": rei.get("OUTBOUND_ENABLED", "false").lower() == "true",
    }
