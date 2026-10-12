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

State/data defects came from treating local defaults, empty arrays and hardcoded values as backend truth. Request lifetime, polling, reload and identity defects explain rendering/performance failures. Swallowed errors, fabricated zeros, stale context, unbounded authentication and inaccessible/clipped content explain edge failures. Repairs preserve existing domain operations and server authority; no governance gate is represented by a cosmetic switch. New/replacement screens introduce no any types.

## Verification and limits

Final measurements: [VALIDATION.json](VALIDATION.json) and [browser evidence](after/evidence.json). Commands: typecheck, lint, frontend API/store tests, clean production build, runtime dependency audit, and test:browser. Regression assertions exercise destination denial, HTTP faults, malformed JSON, bounded signals, 20/200 simultaneous 401s, failed refresh waiters, session isolation, user changes and logout.

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
