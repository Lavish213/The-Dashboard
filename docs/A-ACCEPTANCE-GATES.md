# Acceptance gates for an A

Status on 2026-10-13: substantial repairs verified; full production system is **not A**. Unit test counts are not conversation-quality scores, code coverage or evidence of production uptime. Repair PR #1 has now been merged in Bob-Intelligence-, REI-AGENT, Sophia-Agent and The-Dashboard. This is source integration, not a verified production rollout. Bob/standalone Sophia retain their separately logged open items.

## Verified in this pass

| Boundary | Evidence | Limit |
|---|---|---|
| REI events to Dashboard | Actual pinned REI producer crosses webhook authentication; exact calls/sessions/local lead mapping, real transcript chunks, stable persisted replay receipts | Disposable database; no production transport outage or process crash |
| Dashboard operators | Server pagination/month ranges, full deal aggregates, date validation/cancel acknowledgement, own notifications/admin roster, current active DB roles | Synthetic populated UI data and SQL; no real scheduling provider |
| Realtime authentication | <=20-second one-use tickets, Redis atomic consumption under 40 competing reads, reconnect/cancellation and ownership guards | Connected-session permission/revocation changes still need a policy |
| Fresh database startup | 44 tables/46 enums compare to registered models, disposable rebuild/reinitialization, existing exact schema validation, preserved historical head | Arbitrary legacy data upgrade/rollback not verified |
| Production configuration | Hosted Compose rendering checks private services, removed development mounts/overrides, authenticated Redis, build origins/domain | No container deployment, TLS, recovery, secrets rotation or backup drill |
| UI behavior | 37 rendered states across 16 routes, 14 interactions, zero automated accessibility/runtime errors; 25 frontend regressions | Manual screen reader, Firefox/Safari and production rehearsal open |

## Remaining work in priority order

| Gate | Required implementation or evidence | Completion proof |
|---|---|---|
| Durable voice delivery | Transactional outbox with stable event IDs, bounded retry/backoff, lease/fencing, ordered call creation before dependent events, dead-letter/operator recovery; surface rejected receipts instead of silently dropping them | Kill producer/receiver after write and before acknowledgement, restart, prolonged outage/reordered replay, multiworker concurrency; exactly one persisted outcome and visible terminal failure |
| Governed follow-up execution | Move advisory proposals into the existing authorized approval/workflow path with actor/lead/call binding, expiration, preconditions, idempotent action receipt and audit trail | Approval/rejection/expired/revoked/duplicate scenarios; no campaign or seller action without authority; approval actually executes once |
| Real calendar workflows | Provider availability, timezone/business hours, atomic slot reservation, create/cancel/reschedule receipts and callback jobs with quiet hours/suppression checks | Conflicting concurrent bookings, DST, provider timeout after booking, duplicate retries, cancellation and reschedule recovery; no success claim without receipt |
| Standalone Sophia identity/memory | Close membership/RLS and deterministic verified seller-brief/lead binding; reject caller-controlled or ambiguous identity; preserve approved offer authority | Cross-account/cross-lead denial, replay/stream lease and real memory delivery tests; no unapproved offer or unsupported claim |
| Suppression recovery | Phone call/SMS journal, restart/retry/receipt/lease guards and adapter denial are implemented in REI PR #2. Configure the private persistent volume before enabling outbound operation. Email-address-wide suppression, consent restoration and separate-replica behavior remain open | 38 new source regressions include hard process exit, concurrent requests, outage recovery, alternate lead/adapters, missing storage, voicemail identity/XML and SMS intent; production/shared-volume/provider drills still required |
| Legacy database operations | Reviewed data-preserving upgrade path for each actually deployed schema, credentials/volume protection, backup/restore and rollback | Representative existing records retained through upgrade/rollback; empty initialization is not a substitute |
| Notifications/realtime lifecycle | Internal transactional notification outbox and published delivery receipts; long-lived role/revocation/expiry policy | Commit failure sends no event; worker recovery avoids duplicate effects; connected revoked/demoted user loses authorized channels |
| Tooling dependencies | Remove remaining unpatched braces dependency chain with a deliberate toolchain migration; selector parser compatibility/advisories are repaired in Dashboard PR #2 | Full development audit clear plus clean build, style comparison and all browser/regression gates; runtime audit alone is insufficient |
| Human-quality phone behavior | Representative actual recordings for accents, noise, muffled speech, hearing needs, interruptions, long pauses, multi-topic/long calls, corrections, refusals and voicemail | Human-scored rubric for intelligibility, factual accuracy, identity/disclosure, task completion, interruption repair, natural turn timing; measured provider/VAD/STT/LLM/TTS traces |
| Production provider recovery | STT/TTS/LLM/telephony faults, websocket reconnects, latency budgets, graceful human escalation, monitoring and rollback | Controlled provider outage/load/restart drills with bounded failures and no unacknowledged booking/callback/opt-out claims |

No evidence in this pass establishes perfect accents, indefinite conversation length, human-level speech or a completed production rollout. Remaining implementation gates are explicit; they are not being relabeled as only missing live tests.


Final production-secret refinement verified: [CI 38328837255](https://github.com/Lavish213/The-Dashboard/actions/runs/38328837255) on `bfb85a45d67d6946c004d73d715c8511b1c35a36` is fully green, retaining 1,095 backend cases and all schema/frontend/browser gates. The Compose check now also verifies that production backend/provider secrets are absent from the frontend container environment. Subsequent report commits change only documentation/evidence.


## Merge verification — 2026-10-13

| Repository | Merge commit | Pull request |
|---|---|---|
| Bob-Intelligence- | `113ba05f10ca3dfae6f1ce2daca058808f9c61ef` | https://github.com/Lavish213/Bob-Intelligence-/pull/1 |
| REI-AGENT | `7e12f6bc93c2f7adfd3d325187a7186bd9d6d97d` | https://github.com/Lavish213/REI-AGENT/pull/1 |
| Sophia-Agent | `6d95844792038d12f8daad368a0b7136bc72a459` | https://github.com/Lavish213/Sophia-Agent/pull/1 |
| The-Dashboard | `60346e5c7087d8aef1bca525e31f347df523dc24` | https://github.com/Lavish213/The-Dashboard/pull/1 |

Hosted head checks passed before these merges. REI Vercel preview status passed after the request-time database initialization repair. Local verification reproduced 237 Bob tests, 51 Bob SQL contracts, 55 REI outbox/receipt tests, 30 REI dashboard HTTP checks, the REI scheduling SQL contracts, and the current REI dashboard build/lint without database credentials. The Dashboard verification workflow now also runs on `phase6-transcript-runtime` after merges.

The latest source includes leased and ordered voice event recovery, checkpointed conversation events, live websocket role revalidation, and approval decision lifecycle repairs. These supersede some earlier gaps above, but do not establish that every remaining acceptance requirement is complete. The standalone Sophia repository remains a separate fallback with incompatible shared-schema integration; merging its source does not authorize combining its embedded Bob with the REI schema. Actual provider recovery, external calendar operations, durable suppression recovery, data-preserving legacy upgrades and production operations remain unproven.


## Closest-to-A upgrade pass — 2026-10-13

- REI [PR #2](https://github.com/Lavish213/REI-AGENT/pull/2) merged as `07535d629831040aa808c860a8004506e36b84b0`, after exact-head CI on `95d8c1bab18aa0f23de7500b27ffb1b9bbdb8816` passed. Local full suite: **1,490 tests**, including **38 new** suppression, process-loss, receipt, XML/disclosure and SMS intent cases. SQL checks verify actual append-only evidence privileges. Bob was rechecked with **237 tests and 51 SQL contracts**; the REI dashboard passed **30 HTTP checks**. The current standalone Sophia merge has its existing successful 450-case CI evidence; its code was unchanged in this pass.
- The source now journals phone STOP before datastore lookup/logging; retains normalized phone blocks after remote recovery; fences leased recovery workers; rejects missing/mismatched persistence evidence; and guards final call/SMS adapters. Outbound startup fails closed without a usable `CONTACT_SUPPRESSION_PATH` private persistent volume. This source merge did not configure or rehearse a live volume.
- SMS parsing now separates normal 'send', 'extend', appointment cancellation and 'stop by' text from actual opt-out requests. All English/Spanish voicemail variants disclose AI in the first sentence; customer XML is escaped. Unsupported nearby-closing and market claims, human-buyer email identity and an unimplemented START promise were removed.
- Dashboard [PR #2](https://github.com/Lavish213/The-Dashboard/pull/2) merged as `98eee130ec21626c2a2dcf976384cfd291001122`. Patched selector parser 7.1.6 passed type/lint, **28 frontend cases**, build, browser, backend and configuration CI. The full development dependency audit fell from eight to seven findings: selector-parser advisories cleared, **seven high development-tool findings** remain in the separate braces/glob chain. The shared-contract workflow now pins the actual hardened REI producer.

**Grade limit:** The system is closer to the source acceptance gates, but a full production A is not justified. Overall backend coverage measured **37%** before the final voicemail/parser refinements. Actual phone audio/provider recovery, external calendar operations, email-wide and distributed suppression, arbitrary legacy upgrades, backup/restore, production volume rollout, the remaining vulnerable development chain and human accessibility still need implementation or evidence. Counts of passing tests are not a substitute for these gates. No live seller calls/messages or database migrations were performed.
