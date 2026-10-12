# Repair pass and verification limits

The subsequent screenshot-led repair pass, its 22-item issue log, design contract, before/after screenshots and final browser measurements are in [visual-audit/REPORT.md](visual-audit/REPORT.md). It covers all 16 navigation routes, mobile/light states, error states and auth/navigation interactions using the real production frontend with synthetic APIs. It does not close the production integration gates below.

Confirmed repairs: fail-closed webhook authentication; genuine property provider error/empty states; exact provider-call-to-Sophia-session mapping; session-specific signal/context reset; removal of fabricated KPI history; cancellable list/dashboard queries with errors; API destination/redirect/timeout controls and coalesced refresh; handoff role/identity and participant ownership guards; unconditional media-query hooks, stable dispatcher, session-scoped stream deduplication, server-confirmed subscriptions, and valid CSS import ordering. The existing workflow/governance domain and visual tokens/components remain the foundation.

Architecture, initial tracked-file map and ten-product desk research preceded initial repairs. See the coordinated master log and file map in REI-AGENT `docs/system-audit`. These are static/source audit evidence, not a claim that every runtime path was exercised.

Current recovered checks: 20 isolated backend safety cases; 20 frontend fault/concurrency/store cases; frontend type checking, lint and production build; runtime dependency audit with zero advisories. Evidence is saved under `docs/test-evidence/system-audit`. The restored dashboard polling uses existing TanStack Query instead of overlapping manual intervals. No generated historical data is shown as real performance.

The embedded full SQL harness was unreliable on duplicate-event error/transaction handling; that run is not counted as a pass. Hosted CI run 38282015032 on cf3292812f011288fc8b74a296460d334243ae70 subsequently passed 1,042 backend tests against disposable PostgreSQL 17 and Redis 8, plus the frontend checks. Exact/ambiguous/absent call mapping is included. Full migration head/upgrade, independent production concurrency, event receipts/deduplication, cross-database lead mapping and classification-triggered follow-up governance remain open.

The second review also caught a success toast after local storage failure; save/remove now reports success only after storage accepts the update.

The screenshot-backed visual overhaul remains unverified. Cloud browser capture timed out and the workspace reset; recovered code was committed and rerun. No actual desktop/mobile/keyboard/contrast screenshots were obtained. No A grade, deployment, live call, or completed full-system overhaul is claimed.

Setup: frontend `npm ci --ignore-scripts`, `npm run typecheck`, `npm run lint`, `npm test`, `npm run build`. Backend Python 3.12 and `pip install -r requirements.txt -r requirements-dev.txt`. Set `TEST_DATABASE_URL` and `DATABASE_URL` to the same explicitly disposable loopback PostgreSQL database ending in `_test`, with disposable `REDIS_URL`, then run `pytest tests tests_safety -q`. Test hooks reset the public schema. Never point this at existing data. `KARPATHYS_WEBHOOK_SECRET` and `BATCHDATA_API_KEY` must be configured for their respective integrations; absence returns unavailable.
