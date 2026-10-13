# Repair pass and verification limits

The screenshot-led audit and repair record is [visual-audit/REPORT.md](visual-audit/REPORT.md). It preserves the original findings and adds the current operator, integration and infrastructure pass. Architecture/file mapping and ten-product desk research preceded the initial changes. Source review is not proof that every runtime path was exercised.

## Current verified pass

Dashboard CI [38328169737](https://github.com/Lavish213/The-Dashboard/actions/runs/38328169737), commit `82fb9af6e7fe6d08695e277ce3b77dc9702ef275`, passed 1,094 backend cases on disposable PostgreSQL 17/Redis 8, including exact voice persistence/replays, current database identities and atomic ticket consumption. Frozen-schema initialization, destructive roundtrip ONLY on an explicitly disposable test database, reinitialization/idempotency, model comparison and historical single-head checks passed: 44 tables, 46 enums. The production Compose merge check passed. Frontend type/lint/build, 25 unit/fault tests and runtime dependency audit passed; browser completion is recorded in the visual report after its run finishes. An additional pinned actual REI producer contract is being run on the subsequent source commit; do not count it as passed until its recorded CI outcome.

REI coordinated CI [38328179931](https://github.com/Lavish213/REI-AGENT/actions/runs/38328179931), commit `7b9338d268b809b570fef99dd3c61620b9cabc5b`, reports 1,412 backend cases, 8 Bob/SQL contracts and 30 dashboard HTTP fault checks. These counts describe executable checks, not coverage percentages or production audio success rates. Dashboard safety cases are included in its total.

## Repairs

- Paginated scheduled work and month ranges now originate at the server; deal aggregates cover all matching records. Dates must be explicit, timezone-aware and future-facing; cancellation is an acknowledged null write.
- Lead mutation permissions, notification ownership, administrator-only team access, active/not-deleted authentication and owned realtime channels are enforced. HTTP notification writes commit before publication/acknowledgement.
- Settings reads actual server identity/security durations, own notifications and permitted team data. External voice configuration and booking limitations are explicit. No fabricated controls or trends are presented as functional.
- Account-specific storage/query/conversation state and delayed transcript selection are verified with populated browser fixtures.
- REI canonical endpoints now require versioned matching persisted receipts. The dashboard locks provider-call ingestion, maps external lead IDs to distinct local entities, binds exact call sessions, stores real transcript chunks and deduplicates stable replay receipts. Model dispositions remain advisory proposals; no automatic outbound campaign is triggered by this bridge.
- The production overlay removes inherited public database/service ports, development mounts and environment overrides. Frontend origins are build-time configured or same-origin; the domain reaches Caddy; Redis health uses authentication. Password-bearing Redis URLs and DB readiness exception details are no longer returned/logged. Public proxy access to internal metrics is denied.
- Socket URLs use bounded, single-use Redis tickets instead of reusable JWTs. Each reconnect obtains a new ticket; delayed requests cannot reopen a destroyed client. Database roles are authoritative at connection time.

## Remaining acceptance gates

No A grade is claimed. Open work includes durable REI event outbox/replay through long outages and ordering races; concurrent multiworker crash/recovery drills; approved disposition-action execution; notification outbox for every internal producer; live database upgrade/backup/restore; standalone Sophia membership/RLS and verified memory/brief integration; approved offer authority; atomic external calendar reservation/cancellation/rescheduling; durable suppression recovery; real duplex phone audio, noisy/accented/muffled speech, latency, interruptions and human review; production monitoring/rollback. Long-lived sockets also need a defined policy for role/revocation changes after connection. Cross-browser/manual screen reader coverage and populated production rehearsal remain open. Development dependency audit still has 7 high and 1 moderate advisories in the tooling graph; runtime audit is zero.

No production infrastructure, live callers, calendars or campaigns were changed. Draft PRs preserve the work for review.


Final source verification: [Dashboard CI 38328389520](https://github.com/Lavish213/The-Dashboard/actions/runs/38328389520) on `fef426224ae434d348ed9dc3fe16f121ad97adc6` is fully green: **1,095 backend cases**, including the actual pinned REI producer through webhook authentication and persisted SQL receipts; 44-table/46-enum initialization/schema gates; production Compose checks; 25 frontend cases, type/lint/build/runtime audit and 37 browser states/14 interactions with no automated accessibility or runtime errors. This supersedes the pending producer/browser status above. No real provider calls, production deployment or historical data upgrade was tested.


Final production-secret refinement verified: [CI 38328837255](https://github.com/Lavish213/The-Dashboard/actions/runs/38328837255) on `bfb85a45d67d6946c004d73d715c8511b1c35a36` is fully green, retaining 1,095 backend cases and all schema/frontend/browser gates. The Compose check now also verifies that production backend/provider secrets are absent from the frontend container environment. Subsequent report commits change only documentation/evidence.
