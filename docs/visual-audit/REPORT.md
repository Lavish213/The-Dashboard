# Dashboard forensic repair and visual verification

This pass repairs the existing Dashboard frontend in the four-repository real-estate system. Architecture, tracked-file maps, the ten-product primary-source comparison and coordinated backend issues are in REI-AGENT/docs/system-audit. Nothing was deployed, called, messaged or booked.

## Evidence and approach

Screenshots come from the production Next application with synthetic authenticated API responses and blocked external HTTP requests. Lists use empty fixtures; analytics use explicit synthetic totals. They prove frontend behavior under those inputs, not production data consistency or provider integration. [Design contract](DESIGN-CONTRACT.md), [original dashboard](before/01-dashboard-desktop.png), [original Settings](before/02-settings-desktop.png), [original mobile](before/03-dashboard-mobile.png), [fabricated Analytics](before/07-analytics.png).

Pass 1 captured dashboard, Settings, mobile menu and outage. Pass 2 covered all 16 navigation destinations, light theme, additional mobile screens and six further outages. Source review identified root causes; screenshots and axe identified visual/accessibility defects. An intermediate browser run served stale client output; clean builds were required for final verification. Original and intermediate evidence are preserved separately. after/evidence.json contains the final run.

## Master issue log

| ID | Severity | Root cause and affected files | Repair / verification |
|---|---|---|---|
| UI-01 | High | Default mode falsely implied active Sophia; ModeIndicator, SophiaStatusWidget | Session/call evidence determines activity; unknown/loading explicit. Idle/outage browser checks |
| UI-02 | High | Topbar started green before health request completed | Cancellable query; checking/online/unavailable labels. API health is distinct from voice readiness |
| UI-03 | High | SocialWidget swallowed errors and fabricated zero metrics | Independent queries, cancellation, unavailable/stale labels, retry; outage assertion |
| UI-04 | High | Settings switches were local-only; providers, limits and expiries hardcoded | Remove false controls/values; disclose unavailable configuration. Backend settings router has no endpoints; integration OPEN |
| UI-05 | High | Settings invented administrator/team membership | Show authenticated account; Users-tab assertion. Team administration OPEN |
| UI-06 | Medium | AppShellRuntime notification button had no action | Explicit approvals link to existing route |
| UI-07 | High | Navigation text measured 2.23:1; command hint 2.69:1; light active nav contrast failed | AppNav, NavItem, AppShellRuntime and tokens repaired; axe |
| UI-08 | Medium | MobileNav lacked dialog metadata and forced full reloads | Title/description and Next links; select/close assertion |
| UI-09 | Medium | Weak hierarchy, inconsistent social spacing, nested scroll and cramped actions | PageContainer/AppShell/dashboard responsive layout and work links; inspected screenshots |
| UI-10 | Medium | Route motion ignored preference | AppShell respects reduced motion; browser context uses reduction |
| UI-11 | High | Analytics hardcoded sparkline observations and fabricated weekly calls from all-time totals | Remove invented history; label all-time totals and missing history; cancellable query and error states |
| UI-12 | High | Calendar arrows unnamed; follow-up dates described as appointments | Named controls, truthful description; axe. Actual booking integration OPEN |
| UI-13 | High | Transcript errors appeared empty and earlier response could overwrite selection | Cancellable selection-keyed queries; distinct errors/empty states. List outage tested; populated race runtime test OPEN |
| UI-14 | High | Queries, conversation and approvals could survive user change | Auth/Query providers and auth store isolate/reset identity. Actual Zustand refresh/change/logout regression test |
| UI-15 | High | Properties used one browser storage key across accounts | Account-scoped key. Legacy unknown-owner data preserved but not displayed/migrated; persisted cross-account runtime test OPEN |
| UI-16 | High | Calls clipped mobile columns; empty scrolling lead board inaccessible to keyboard | Calls/Audit tables and Leads board use focusable horizontal scroll regions; mobile screenshot/axe |
| UI-17 | Medium | Funnel white-on-bright values and faded property helper text failed contrast | Readable values/helper text; axe |
| UI-18 | High | Deals/Follow-ups/Calendar swallowed errors; list empty states also appeared during errors | Cancellable queries where applicable, persistent errors, suppress false empty claims, unknown metric markers; outage checks |
| UI-19 | High | Login/refresh unbounded; refresh parsed unused stored JSON; auth guard ignored status changes | Bounded requests, reject redirects, shared login, reactive guard, readable errors and sign-out; logout/structured rejection browser tests |
| UI-20 | Medium | Error toast used wrong theme and 4.34:1 text contrast | ToastProvider matches theme and uses contrast-safe tokens; social outage axe |
| UI-21 | High, partial | Calendar/Follow-ups only load first 200 leads; Deals first 200 per status | Truncation explicitly disclosed. Complete server-side scheduling queries/pagination OPEN |
| UI-22 | Medium, open | Runtime contracts reference missing GOVERNANCE_RULES.md | Missing canonical document logged; authoritative policy must be restored |
| UI-23 | High, open | Development tooling dependency advisories: braces/glob/Tailwind lint chain, brace-expansion, browserslist and selector parser | Full dependency audit records 9 high and 1 moderate finding. Runtime audit is zero. Compatible leaf patches and a verified toolchain migration remain required; do not blindly downgrade Next lint config or migrate Tailwind to silence counts. Raw evidence: development-dependency-audit.json |

State/data defects came from treating local defaults, empty arrays and hardcoded values as backend truth. Request lifetime, polling, reload and identity defects explain rendering/performance failures. Swallowed errors, fabricated zeros, stale context, unbounded authentication and inaccessible/clipped content explain edge failures. Repairs preserve existing domain operations and server authority; no governance gate is represented by a cosmetic switch. New/replacement screens introduce no any types.

## Verification and limits

Final measurements: [VALIDATION.json](VALIDATION.json) and [browser evidence](after/evidence.json). Commands: typecheck, lint, frontend API/store tests, clean production build, runtime dependency audit, and test:browser. Regression assertions exercise destination denial, HTTP faults, malformed JSON, bounded signals, 20/200 simultaneous 401s, failed refresh waiters, session isolation, user changes and logout.

Hosted CI [38288551534](https://github.com/Lavish213/The-Dashboard/actions/runs/38288551534) passed on source commit 06f7a063323dd96b91a929bb88e7e8ff987fc750: 1,042 PostgreSQL/Redis backend tests, 22 frontend tests, build/typecheck/lint, runtime audit and all 31 browser states with a matched installed browser. These counts are separate; screen states are not additional backend tests. Subsequent edits only record evidence and findings.

Local Chromium is 134.0.6998.35 because current archives failed through the download proxy. The pinned current Playwright drives an isolated fixture-only browser. CI installs a matched browser and repeats verification; local results do not prove current Chrome, Safari or physical iPhone compatibility. Screenshots show viewport-visible content with inner scrolling. Axe results cover tested states, not accessibility certification.

Dynamic detail routes, populated long lists, approval execution, drag/drop persistence, property provider search, persisted identity isolation, websocket recovery, every permission role and real infrastructure still require runtime testing. Source repairs to those paths do not count as successful phone calls or production tests.

## Remaining A-grade gates

The coordinated system log still tracks REI ingest receipts/prefix/idempotency and lead mapping; governed transcript/follow-up binding; fresh migration parity; real availability/reservation/cancel/reschedule; approved quotes; signed single-use callback/stream leases; durable suppression; attributable Bob owner facts; membership/RLS; and real audio/provider recovery. UI screenshots do not close these.

For this dashboard, complete configuration/team/notification APIs, full scheduled-work pagination, populated interaction tests, all roles, modern cross-browser/assistive-technology testing and a production-connected rehearsal remain required. No A grade, numeric coverage gain or live conversation quality is claimed.

## Journey health

| Step | Description | Health |
|---|---|---|
| 1 | Sign-in/session | Improved; rejection/logout verified, deployment auth untested |
| 2 | Dashboard overview | Repaired and fixture-verified |
| 3 | Navigation/mobile access | Repaired; populated interactions need expansion |
| 4 | Analytics/social/list errors | Tested repairs; complete pagination remains partial |
| 5 | Settings/operator identity | Truthful and accessible; configuration integration open |
| 6 | Production voice/approvals/appointments | Open integration gates |


## Enhancement and integration pass — 2026-10-13

This supersedes the earlier open configuration/pagination/populated-fixture statements for the specific repairs below. The original pass and its exact historical evidence remain above. This is an operator dashboard enhancement, not proof of external appointments or human-quality voice.

| ID | Severity | File/boundary; root cause | Repair and verification |
|---|---|---|---|
| UI-24 | High | leads API / Follow-ups / Calendar; first 200 records silently looked complete | Server scheduling/month filters, stable pages and load-more; 201-record fixtures and SQL page-2 checks |
| UI-25 | High | Deals; totals and average were calculated from loaded pages | SQL full-set counts/score sums with correctly weighted total; 203-record populated check |
| UI-26 | High | notifications routes; caller could select another user | Own feed/read counts; cross-account 403/404 and administrator-only creation; SQL and denial-before-DB cases |
| UI-27 | High | settings routes/components; server/team/notification panels unwired | Actual read-only configuration, own acknowledged feed and admin-only paginated roster; permitted/operator browser checks |
| UI-28 | High | lead mutations; malformed/past/naive dates and read-only role writes | LEADS_WRITE enforcement, strict dates, explicit cancellation and server acknowledgement; safety and SQL tests |
| UI-29 | High | realtime endpoint/subscriptions; JWT role trusted and user channels unscoped | Current active DB identity, own-channel enforcement, missing/deleted/inactive denial |
| UI-30 | High | WebSocket URL / proxy logs; reusable JWT in request URI | Authenticated 20-second one-use tickets, atomic Redis consume, reconnect refresh and destroyed-client tests |
| UI-31 | High | production Compose/Docker; inherited development credentials, ports and mounts; localhost browser build | Explicit production env, reset ports/mounts, build-time or same-origin browser URLs, authenticated Redis health/domain; hosted merge check |
| UI-32 | High | backend Docker and schema initialization; no production startup command; fresh schema drift | Guarded frozen snapshot initialization, exact model/enum verification, preserved historical head; 44-table/46-enum disposable roundtrip |
| UI-33 | High | REI ingest / Sophia bridge; wrong prefix/fields, false success, cross-DB IDs and unsafe classification actions | Persisted receipts, mapped external IDs, exact call sessions, chunks, dedup/conflict rejection, advisory-only proposals; SQL regressions |
| UI-34 | Medium | redis logger / readiness route; credential URL and exception details exposed | Remove URL logging and public exception detail; source checked |

Enhanced fixture browser runner covers 37 states across all 16 navigation routes and 14 interactions, including page 2, notification failed-write/retry, operator/admin separation, delayed transcript races and persisted account isolation. Exact latest results are in `enhanced/evidence.json`; fixture screenshots are synthetic and are not production seller data. Automated accessibility checks supplement visual inspection; they do not prove manual assistive-technology usability. Screenshot audit inspected populated Calendar, Deals, Settings and Follow-ups views.

Latest backend/Compose verified CI: [38328169737](https://github.com/Lavish213/The-Dashboard/actions/runs/38328169737) on `82fb9af6e7fe6d08695e277ce3b77dc9702ef275`: 1,094 backend cases and schema gates passed; frontend 25 cases/type/lint/build/runtime audit passed. An additional actual producer-contract test is tracked on the subsequent source commit. Runtime advisories: 0. Full development graph: 7 high, 1 moderate; do not interpret runtime zero as a clean whole toolchain.

| Journey step | Description | Current health |
|---|---|---|
| Sign-in and identity | Login/logout, role-scoped APIs and isolated account state | Verified in code/fixtures/disposable SQL; live deployment open |
| Overview | Honest readiness, idle state and all-time totals | Fixture verified |
| Navigation and access | Desktop/mobile/light/error states and keyboard-accessible controls | 37-state automation; manual multi-browser/a11y open |
| Scheduled work | Server pages/month ranges, acknowledged follow-up dates and all-page deal totals | Populated fixture and SQL verified; external bookings open |
| Settings | Read-only server/security/team and own notification feed | Role/ownership and mutation failure/retry verified |
| Voice and execution | Exact persisted bridge and advisory disposition proposals | SQL/producer contracts; durable delivery, approved execution and real calls open |


Final source verification: [Dashboard CI 38328389520](https://github.com/Lavish213/The-Dashboard/actions/runs/38328389520) on `fef426224ae434d348ed9dc3fe16f121ad97adc6` is fully green: **1,095 backend cases**, including the actual pinned REI producer through webhook authentication and persisted SQL receipts; 44-table/46-enum initialization/schema gates; production Compose checks; 25 frontend cases, type/lint/build/runtime audit and 37 browser states/14 interactions with no automated accessibility or runtime errors. This supersedes the pending producer/browser status above. No real provider calls, production deployment or historical data upgrade was tested.


Final production-secret refinement verified: [CI 38328837255](https://github.com/Lavish213/The-Dashboard/actions/runs/38328837255) on `bfb85a45d67d6946c004d73d715c8511b1c35a36` is fully green, retaining 1,095 backend cases and all schema/frontend/browser gates. The Compose check now also verifies that production backend/provider secrets are absent from the frontend container environment. Subsequent report commits change only documentation/evidence.


## Recovery and approval verification — 2026-10-13

Latest source `f1227830231869533f5c433d1b62fdf196b93d08` passes [CI 38346907132](https://github.com/Lavish213/The-Dashboard/actions/runs/38346907132). The completed backend job reports **1,120 passed**; the frontend job reports **28 passed**, with typecheck, lint, production build, runtime dependency audit and browser verification successful. Production configuration checks also pass. Vercel reports success for this source; that status does not establish a deployed backend, configured providers or real caller readiness.

The boundary job uses the actual pinned REI producer at `44e3b54ae8537d80d7c3896bc2f43b4b54e66101` through HTTP and PostgreSQL. It passes two producer restarts, an outage before the receiver writes, and lost acknowledgement after commit. This closes those specific delivery tests; extended outages, dead-letter operation, multi-host durability and deployment drills still require evidence.

Approval repairs bind authenticated actors and workflow authorization, serialize decisions, process escalated/expired approvals and preserve errors until acknowledged writes. The browser runner adds operator/reviewer/expired authority scenarios. Actual campaign/calendar execution remains an open integration gate. Long-lived socket reauthorization has source regressions; live provider recovery remains open.

At this checkpoint all three PRs remain unmerged. REI regression CI passes but its Vercel status fails; standalone Sophia previously had no PR workflow and now receives an automated regression workflow. This is a repair-readiness checkpoint, not an overall A grade. Earlier counts and open statuses above are historical and are superseded only for the named boundaries.
