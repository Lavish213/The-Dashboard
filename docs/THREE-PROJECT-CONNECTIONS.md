# Bob, Sophia and dashboard connection contract

Canonical components: Bob-Intelligence- worker, REI-AGENT Sophia service, and The-Dashboard API/frontend. The separate Sophia-Agent repository is not an interchangeable shared-schema runtime.

## Required edges

| From → to | Transport | Verification |
|---|---|---|
| Bob → shared REI Supabase | Tenant-bound brief/decision/outbox RPCs | Bob contract 2.1, lease generation, atomic snapshots and receipt checks |
| Bob → Sophia | POST /api/ingest/bob/brief-created | Current committed Bob event, tenant, event ID, service secret and persisted acknowledgement |
| Sophia → Bob | Shared database fact RPC with local fact outbox | Exact lead/call provenance, fact receipts, retries and generation checks |
| Sophia → dashboard | /api/v1/ingest call/turn/transcript/business lifecycle | Local persistent delivery journal, authenticated HTTP, exact receipts and replay checks |
| Dashboard → Sophia | /api/operations commands/reviews | Authenticated dashboard role, server-derived actor, service secret, current source fingerprint and command receipt |
| Browser → dashboard | Authenticated REST and ticketed WebSocket | Correct build-time API/WS origins, CORS, current role and reconnect/revocation checks |

The shared Bob/Sophia Supabase database and the dashboard's own PostgreSQL database are distinct storage roles. Never point dashboard initialization/schema-reset tooling at the shared source database. Apply reviewed source migrations in order through 20261019 and the matching Bob migrations against a representative clone before touching production.

## Configuration alignment

Use one canonical externally reachable HTTPS Sophia origin and one canonical dashboard API origin for the preflight topology below. Advanced private/public aliases need an explicit network design; do not weaken checks to hide a mismatch.

| Configuration | Bob | Sophia | Dashboard backend |
|---|---|---|---|
| Source Supabase project | SUPABASE_URL | Same SUPABASE_URL | Not the dashboard DATABASE_URL |
| Source access | SUPABASE_SERVICE_KEY | SUPABASE_SERVICE_KEY | Source data enters via authenticated ingestion |
| Source tenant | BOB_TENANT_ID | Same TENANT_ID | Same REI_SOURCE_TENANT_ID |
| Sophia origin | REI_COMMAND_URL, or explicit BOB_EVENT_URL including the full brief-created path | PUBLIC_URL for provider-signature verification | REI_COMMAND_URL |
| Dashboard API origin | No direct Bob→dashboard event URL | KARPATHYS_URL | Browser NEXT_PUBLIC_API_URL, or an actual same-origin proxy |
| Event authentication | KARPATHYS_WEBHOOK_SECRET | Same value | Same value |
| Reverse command authentication | Not required | SOURCE_COMMAND_SECRET | Same value |

Bob's explicit BOB_EVENT_URL overrides its REI_COMMAND_URL alias. Leaving both blank disables optional event transport. Configure a private durable mount for Sophia's VOICE_FACT_OUTBOX_PATH, KARPATHYS_OUTBOX_PATH, CONTACT_SUPPRESSION_PATH, COMMUNICATION_JOURNAL_PATH and WORKFLOW_JOURNAL_PATH. A valid absolute path does not prove persistence or multi-replica consistency. Keep outbound disabled until operational acceptance; enabling background jobs is a separate decision from configuring connection recovery.

For separate frontend/backend deployments, build the frontend with NEXT_PUBLIC_API_URL set to the canonical dashboard API HTTPS origin and NEXT_PUBLIC_WS_URL to the corresponding WSS origin. A frontend rebuild is required when public build-time values change. Blank origins only work behind a real proxy routing API and WebSocket traffic to the backend. The provided Caddy topology is one implementation; declare DASHBOARD_SAME_ORIGIN_PROXY=true to acknowledge that topology in the offline checker. That declaration itself does not verify a proxy. A standalone Vercel frontend has no backend rewrite in the current next.config.ts; blank API settings must not be assumed to connect it automatically.

From the dashboard repository, with private, untracked configuration exports:

For a split frontend/API deployment, include `DASHBOARD_FRONTEND_ORIGIN` in the
dashboard preflight export with the frontend's actual HTTPS origin (no path or
trailing slash), and include the backend's actual `CORS_ORIGINS` value. This
preflight-only origin declaration does not change the backend allowlist. The
checker requires explicit frontend membership in the JSON-array or comma-separated
allowlist; an API health check alone cannot establish browser access. Preserve
other required origins when correcting the deployed allowlist, then redeploy the
backend and verify an OPTIONS request with the frontend Origin, POST method and
content-type header succeeds before testing authenticated login.

```bash
python backend/scripts/verify_project_wiring.py --bob-env /private/bob.env --rei-env /private/sophia.env --dashboard-env /private/dashboard.env
```

This read-only preflight prints field/problem names without URLs, tokens or source credentials. Exit 2 means missing/misaligned settings. Exit 0 means configuration_consistent, not connected, deployed, licensed, consented, or production ready. The script does not interpolate shell expressions or .env references. Supply resolved values. --allow-loopback permits HTTP/WS only on loopback for disposable tests; production origins must use HTTPS/WSS. Separate service keys for the same shared Supabase project are permitted. Secrets belong in each deployment's private settings and never in NEXT_PUBLIC variables or the frontend environment.

## Authenticated round trip and dashboard status

The source review page now displays Project connections with explicit loading, unavailable, wrong-receiver and degraded states, a check timestamp, and separate outbound/background flags. Its authenticated /api/v1/source-review/connections API checks the dashboard database and sends a fresh UUID challenge to Sophia's /api/operations/integration using SOURCE_COMMAND_SECRET. Sophia queries the shared Bob contract/worker health and local fact/delivery journals, then calls back to /api/v1/ingest/connection using KARPATHYS_WEBHOOK_SECRET. Challenges, schema, service identity and tenant must match. The receiver's identity is a SHA256 of its configured database hostname/port/name plus source tenant; credentials are excluded. The requesting dashboard compares that identity with its own, so a reachable different dashboard database is not reported healthy.

This fingerprint identifies configured storage endpoints, not the physical database server, restored data generation, or cryptographic deployment provenance. Alternate database host aliases can identify the same database differently; align the declared topology deliberately. The probe performs no seller action, quote, call, invitation, booking or provider request. Existing source and dashboard role/service boundaries remain in force. Source snapshots reject a different tenant when REI_SOURCE_TENANT_ID is explicitly configured. Runtime health reports do not authenticate the underlying sold-sale evidence or grant contact/offer permission.

## Verification scope

New focused tests cover derived Bob URL selection, invalid origins, configuration drift/secret redaction, both authentication boundaries, wrong tenant/schema/challenge/receiver, missing Bob/schema/storage, disabled outbound, and degraded status. The existing coordinated suites verify Bob/Sophia shared SQL contracts and actual producer/consumer money/fact boundaries, plus dashboard PostgreSQL and authenticated voice/business transport across process restarts and lost acknowledgements.

The added verify_project_connections.py launches two actual loopback HTTP services and calls the actual dashboard→Sophia→dashboard code against a disposable dashboard database. It denies missing/wrong secrets and checks the receiver binding. Bob worker/health results in this specific harness are explicitly fixtures; it does not claim to execute the actual Bob worker against a live shared database. Separate Bob SQL and source tests cover that contract. The browser audit includes connected, wrong-receiver and unavailable states. These checks complement each other; none is a production/provider-delivery test.

## Live deployment finding

On October 16, 2026 UTC, the last inspected merged source commit still had a Railway Deployment failed status. The dashboard's historical success URL returned Railway Application not found for /api/health, rather than an application-specific missing route. Its cause cannot be determined from a status badge. Hosting/database connections are not installed in this session and runtime credentials are absent; project code access is available. Do not relabel that state as a confirmed running system, invent a deployment error, or rewrite a valid health route without logs. Actual deployment settings/logs, served commit IDs, database baseline and mounts, provider accounts, and current lawful contact/data authority still require live acceptance.

Remaining acceptance also includes provider SMS/email status persistence/reconciliation, actual external-calendar synchronization, real audio/conversation evaluation and independent San Joaquin sold/condition/renovation outcomes. This connection patch does not close those separate implementation/data gates or claim every feature has live end-to-end evidence.
