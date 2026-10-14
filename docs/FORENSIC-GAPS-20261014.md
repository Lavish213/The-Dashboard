# Current forensic gaps — 2026-10-14

**59 prioritized findings: 34 reproduced findings, 16 source-confirmed findings, 3 conditional risks, and 6 acceptance blockers.** The isolated campaign observed 38 counterexamples. Several probes exercise different symptoms of the same root cause; neither count is a production coverage percentage.

The audited merged heads are:

- Bob: [44059af67668](https://github.com/Lavish213/Bob-Intelligence-/commit/44059af6766811add52cf7849dda7ea36e8e164c)
- Sophia: [0ae65ff799eb](https://github.com/Lavish213/REI-AGENT/commit/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263)
- Dashboard: [4b8c556c94d1](https://github.com/Lavish213/The-Dashboard/commit/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5)

Static backend inventory plus focused manual tracing and isolated current-source counterexample probes. Not exhaustive proof that no other bugs exist. No production access, messages, migrations or deployment. Old repaired issues are not counted as newly open findings.

Automated AST inventory covered **541 backend Python files**. Focused review traced the active pricing/permission, scouting, messaging, booking, replay, identity, setup and dashboard data paths. Inventory scanning is not a claim that every branch or production deployment was manually verified. Probe adapters were synthetic; they performed no real provider requests or datastore writes. Dashboard database probes use controlled in-memory adapter behavior and are not a replacement for actual PostgreSQL tests.

## Highest-priority release stops

1. Close the anonymous InstantDM write boundary and enforce write roles on legacy dashboard routes.
2. Bind outgoing prices to complete, dated operator approvals for the actual amount/property/call. Preserve evidence age and retire cached legacy price authority.
3. Make unsubscribe and outbound-channel control durable and universal. Reconcile accepted messages before retry.
4. Consolidate canonical lead/property identities, source scheduling and durable discovery; stop equating a scraped count with saved leads.
5. Connect governed operational state across both databases and the actual calendar/providers; the property evidence panel alone does not complete this workflow.

## Findings

| ID | Severity | Evidence | Project | Finding |
|---|---|---|---|---|
| G01 | Critical | reproduced | Sophia | [Offer threshold checks caller price instead of outgoing amount](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/voice/tools.py#L265) |
| G02 | High | reproduced | Sophia | [Missing permission expiry is treated as valid](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/contracts/intel_packet.py#L110) |
| G03 | High | source_confirmed | Sophia | [Operator access and legacy service-key queries lack tenant enforcement](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/api/security.py#L30) |
| G04 | High | source_confirmed | Sophia | [Canonical property repair is bypassed by legacy queries](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/lib/db.py#L110) |
| G05 | High | source_confirmed | Sophia | [Intel assembly resets evidence timestamps without new evidence](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/lib/intel_assembler.py#L37) |
| G06 | High | reproduced | Sophia | [Date-only closed sales lose recency](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/calculator.py#L31) |
| G07 | High | reproduced | Sophia | [Duplicate comps inflate legacy confidence](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/calculator.py#L66) |
| G08 | High | reproduced | Sophia | [Invalid comps re-enter the no-area median](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/calculator.py#L66) |
| G09 | Medium | reproduced | Sophia | [Configured MAO multiplier is ignored](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/calculator.py#L66) |
| G10 | High | reproduced | Sophia | [Homeharvest asking prices can become ARV](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/homeharvest.py#L11) |
| G11 | High | reproduced | Sophia | [LOW confidence passes the Homeharvest write gate](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/homeharvest.py#L119) |
| G12 | Medium | reproduced | Sophia | [Homeharvest writes negative MAO](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/homeharvest.py#L119) |
| G13 | High | reproduced | Sophia | [Redfin comp request ignores resolved region](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/redfin.py#L46) |
| G14 | High | reproduced | Sophia | [Social and eviction runners count unsaved results](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/social_scraper.py#L90) |
| G15 | High | reproduced | Sophia | [Main scout cycle omits configured source runners](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/cron.py#L156) |
| G16 | Medium | source_confirmed | Sophia | [RSS source is empty and lacks operational coverage](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/rss_scraper.py#L66) |
| G17 | High | source_confirmed | Sophia | [Expired/FSBO property candidates do not create leads](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/expired.py#L17) |
| G18 | High | source_confirmed | Sophia | [Automatic enrichment may receive property ID instead of lead ID](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/cron.py#L48) |
| G19 | High | source_confirmed | Sophia | [Lead insertion and reverse-link update are not atomic or retry-safe](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/lib/db.py#L61) |
| G20 | High | reproduced | Sophia | [Legacy mutations can claim success on zero saved rows](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/api/routes/leads.py#L125) |
| G21 | High | reproduced | Sophia | [Email unsubscribe acknowledges lost writes](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/api/routes/email_webhook.py#L212) |
| G22 | High | reproduced | Sophia | [Email adapter ignores disabled outbound and suppression](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/email.py#L90) |
| G23 | High | reproduced | Sophia | [Accepted SMS becomes failure after logging outage](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/sms.py#L39) |
| G24 | High | reproduced | Sophia | [Deal blast records failed channels as sent](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/deal_blast.py#L7) |
| G25 | High | risk | Sophia | [Deal blast send-before-log race allows duplicates](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/deal_blast.py#L7) |
| G26 | Medium | reproduced | Sophia | [Walkthrough email caller has incompatible arguments](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/workflows/engine.py#L46) |
| G27 | High | reproduced | Sophia | [Completed walkthrough still triggers no-show reminder](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/voice/appointment_scheduler.py#L48) |
| G28 | High | reproduced | Sophia | [Email-only nurture cannot advance without SMS drip date](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/email.py#L135) |
| G29 | High | source_confirmed | Sophia | [Inbound email conversation is not wired](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/email.py#L185) |
| G30 | High | risk | Sophia | [Speed-to-lead scheduled touches are memory-only](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/speed_to_lead.py#L159) |
| G31 | High | reproduced | Sophia | [Poison lead aborts dashboard refresh page](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/karpathys/outbox.py#L45) |
| G32 | Critical | reproduced | Dashboard | [InstantDM writes are unauthenticated and unsigned](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/instantdm_webhook.py#L12) |
| G33 | Medium | reproduced | Dashboard | [Any long text containing a digit is labeled an address and hot lead](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/instantdm_webhook.py#L12) |
| G34 | High | reproduced | Dashboard | [InstantDM retries create duplicate social leads](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/instantdm_webhook.py#L12) |
| G35 | High | reproduced | Dashboard | [Legacy dashboard writes have login but no write permission](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/social.py#L74) |
| G36 | High | reproduced | Dashboard | [Social/email delivery state can be manufactured](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/email_drip.py#L97) |
| G37 | High | reproduced | Dashboard | [Curator fetch permits private server URLs](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/curator.py#L39) |
| G38 | Medium | reproduced | Dashboard | [Missing-model fallback fabricates a recent closing](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/curator.py#L50) |
| G39 | Medium | reproduced | Dashboard | [Manual source deduplication is scoped to actor](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/lead_creation.py#L11) |
| G40 | High | reproduced | Dashboard | [Soft-deleted leads remain available in detail/mutations](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/leads.py#L146) |
| G41 | High | reproduced | Dashboard | [Refresh token rotation is not atomic](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/auth.py#L98) |
| G42 | High | source_confirmed | Dashboard | [Logout revokes access token but not refresh family](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/auth.py#L129) |
| G43 | Medium | reproduced | Dashboard | [Legacy malformed business snapshot causes read failure](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/business_evidence.py#L124) |
| G44 | High | reproduced | Dashboard | [Valuation ingest accepts comps without price or closed date](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/business_evidence.py#L12) |
| G45 | High | reproduced | Dashboard | [Existing external lead mapping never refreshes missing contacts](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/voice_ingest.py#L60) |
| G46 | High | source_confirmed | Dashboard | [Operational lead/calendar/deal state is not fully synchronized](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/business_evidence.py#L76) |
| G47 | High | source_confirmed | Dashboard | [Development admin seeding contains a fixed credential](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/scripts/seed_admin.py#L14) |
| G48 | Medium | source_confirmed | Dashboard | [Bootstrap is platform-specific and advertises the wrong password](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/scripts/dev/bootstrap.sh) |
| G49 | Medium | source_confirmed | Dashboard | [Rate limiting module is empty](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/security/rate_limits.py) |
| G50 | Medium | source_confirmed | Sophia | [Synchronous database calls block async legacy routes](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/api/routes/leads.py#L16) |
| G51 | High | source_confirmed | Sophia | [Shared REI/Bob clean baseline is incomplete](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/supabase/migrations/20260911_tenant_and_suppression.sql) |
| G52 | Medium | source_confirmed | Sophia | [Old audit summaries conflict with merged state](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/docs/system-audit/MASTER-ISSUES.md) |
| G53 | High | blocked | Bob | [Current San Joaquin sold-data acceptance is missing](https://github.com/Lavish213/Bob-Intelligence-/blob/44059af6766811add52cf7849dda7ea36e8e164c/docs/VALUATION-MODEL-RESEARCH-AND-GRADE.md) |
| G54 | High | blocked | Bob | [Public county candidate evidence is not deal underwriting](https://github.com/Lavish213/Bob-Intelligence-/blob/44059af6766811add52cf7849dda7ea36e8e164c/docs/SAN-JOAQUIN-LEAD-SAMPLE-20261014.json) |
| G55 | High | risk | Bob | [Queue quarantine and evidence expiration require operations ownership](https://github.com/Lavish213/Bob-Intelligence-/blob/44059af6766811add52cf7849dda7ea36e8e164c/backend/worker/loop.py#L22) |
| G56 | High | blocked | Dashboard | [Production/provider end-to-end acceptance is not available](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/docs/END-TO-END-BUSINESS-EVIDENCE.md) |
| G57 | High | blocked | Sophia | [Persistent volume and multi-replica behavior is unverified](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/docs/BOB-RECOVERY-REAUDIT.md) |
| G58 | High | blocked | Sophia | [Real voice quality and conversations are not measured](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/docs/system-audit/CALIFORNIA-VOICE-ACCEPTANCE.md) |
| G59 | High | blocked | Dashboard | [Legacy production migration and rollback remain unproven](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/docs/database/AUDIT_TABLES.md) |

## Evidence and required fixes

### G01 — Offer threshold checks caller price instead of outgoing amount

**Critical · reproduced · Sophia**

Source: [backend/voice/tools.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/voice/tools.py#L265)

With OUTBOUND_ENABLED=true, quote permission and a $300k threshold, no seller-mentioned price allows a cached $380k–$400k range. _verified_offer_range does not require a dated approved offer row.

Impact: Above-threshold or stale heuristic prices can be spoken when otherwise authorized tools are enabled. This is not an anonymous or disabled-outbound bypass.

Required repair: Bind price actions to an unexpired persisted operator approval for the actual lead, property, amount and call; compare the actual outgoing amount before speech or send.

Acceptance check: Execute full call-bound price tools below/at/above the threshold with absent, stale, revoked, wrong-property and conflicting approvals.

Probe evidence: R14 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G02 — Missing permission expiry is treated as valid

**High · reproduced · Sophia**

Source: [backend/contracts/intel_packet.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/contracts/intel_packet.py#L110)

A permission with a level but no expires_at returns not expired. The gate validates the level, not a complete dated approval identity.

Impact: Legacy grants can remain effective indefinitely.

Required repair: Require a complete scoped grant with bounded expiry and independently verified operator provenance.

Acceptance check: Reject missing/blank/naive/expired/future-invalid grants; verify revocation during a call.

Probe evidence: R15 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G03 — Operator access and legacy service-key queries lack tenant enforcement

**High · source_confirmed · Sophia**

Source: [backend/api/security.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/api/security.py#L30)

Any accepted operator/admin account in the project passes middleware; get_operator_user checks role without configured tenant membership. Numerous service-key reads/writes omit tenant predicates.

Impact: Cross-tenant exposure or writes if another tenant/account exists; live exploitation was not tested.

Required repair: Bind authenticated principals to configured tenant and enforce tenant scope in centralized data access.

Acceptance check: Two-user/two-tenant integration tests covering every operator read and mutation; service-role and RLS checks.

### G04 — Canonical property repair is bypassed by legacy queries

**High · source_confirmed · Sophia**

Source: [backend/lib/db.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/lib/db.py#L110)

18 reverse-relationship references remain across API, alerts, engagement and db helpers. Intel assembly also prefers properties.lead_id before the canonical lead.property_id.

Impact: Wrong, missing or list-shaped property data can affect queue, activation, outreach and cached pricing.

Required repair: Consolidate all property reads through canonical lead.property_id and reject ambiguous or cross-tenant bindings.

Acceptance check: Real PostgREST contracts with inconsistent forward/reverse links, multiple reverse rows and missing properties.

### G05 — Intel assembly resets evidence timestamps without new evidence

**High · source_confirmed · Sophia**

Source: [backend/lib/intel_assembler.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/lib/intel_assembler.py#L37)

Existing seller facts and property prices are labeled updated_at=now, source=comps, regardless of their original timestamps or whether new comps were obtained.

Impact: Old evidence can look current and unrelated cached prices can look sourced.

Required repair: Preserve source record timestamps, origin and reviewed valuation identity; distinguish assembled_at from observed_at.

Acceptance check: Assemble twice without source changes and ensure source age never refreshes.

### G06 — Date-only closed sales lose recency

**High · reproduced · Sophia**

Source: [backend/comps/calculator.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/calculator.py#L31)

A date-only sold_date parses as naive; subtracting aware UTC raises internally and returns None.

Impact: Recent, old and future date-only sales enter unknown-date weighting rather than reliable freshness checks.

Required repair: Parse canonical sale dates explicitly and reject stale, future or unknown evidence for pricing.

Acceptance check: Date-only, zoned, naive timestamp, future and old-sale cases.

Probe evidence: R01 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G07 — Duplicate comps inflate legacy confidence

**High · reproduced · Sophia**

Source: [backend/comps/calculator.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/calculator.py#L66)

Repeating one comp five times returns high confidence. No parcel/sale identity, arm-length, condition or provenance validation precedes the estimate.

Impact: One sale can masquerade as broad market support.

Required repair: Keep this engine out of price authority; use Bob reviewed-sale evidence and deduplicate before reconciliation.

Acceptance check: Duplicate parcel/sale IDs and source lineage tests through the pricing persistence path.

Probe evidence: R02 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G08 — Invalid comps re-enter the no-area median

**High · reproduced · Sophia**

Source: [backend/comps/calculator.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/calculator.py#L66)

With subject area missing, a $900k comp with zero area is excluded from PPSF but re-enters the raw-price median; a valid $100k sale yields a $500k estimate.

Impact: Invalid rows materially change valuations.

Required repair: Use one validated comp set for every branch; withhold unsupported subject/value calculations.

Acceptance check: Invalid-price/area and mixed-type rows must not affect any reconciliation branch.

Probe evidence: R03 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G09 — Configured MAO multiplier is ignored

**Medium · reproduced · Sophia**

Source: [backend/comps/calculator.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/calculator.py#L66)

MAO_MULTIPLIER is loaded but the output calculation always uses 70 percent.

Impact: Operator configuration does not produce the requested underwriting policy.

Required repair: Use validated integer basis points or remove the misleading setting; publish the applied policy.

Acceptance check: Multiple multiplier settings with independently calculated cent-level results.

Probe evidence: R04 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G10 — Homeharvest asking prices can become ARV

**High · reproduced · Sophia**

Source: [backend/comps/homeharvest.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/homeharvest.py#L11)

When sold_price is absent the calculator falls back to list_price. The search uses city/state rather than the supplied subject address; baths is unused.

Impact: Asking prices or unrelated city sales can be presented as comparable evidence.

Required repair: Require verified closed sale prices, subject geography/type/condition and reviewed adjustment evidence.

Acceptance check: List-price-only data must withhold value; geographic and sale-status mismatch tests.

Probe evidence: R05 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G11 — LOW confidence passes the Homeharvest write gate

**High · reproduced · Sophia**

Source: [backend/comps/homeharvest.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/homeharvest.py#L119)

get_comps emits uppercase LOW; trigger_arv_computation checks lowercase low and writes the value. Other emitters use HIGH/MEDIUM, while the voice range reader accepts only lowercase high/medium.

Impact: A weak estimate can overwrite the common price fields used by other modules.

Required repair: Use a typed confidence contract and only persist clearly distinguished reviewed advisory values.

Acceptance check: Single-comp LOW report cannot update a reviewed property valuation.

Probe evidence: R06 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G12 — Homeharvest writes negative MAO

**Medium · reproduced · Sophia**

Source: [backend/comps/homeharvest.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/homeharvest.py#L119)

A $10k estimate writes a negative $18k screening MAO. This branch does not share the newer nonnegative money safeguards.

Impact: Invalid purchase limits persist and differ between engines.

Required repair: Unify bounded integer-cent calculation and infeasibility semantics.

Acceptance check: Low value/high repair scenario must return infeasible or zero screening limit.

Probe evidence: R07 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G13 — Redfin comp request ignores resolved region

**High · reproduced · Sophia**

Source: [backend/comps/redfin.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/comps/redfin.py#L46)

Different region_url inputs produce identical GIS request parameters. RADIUS_MILES is not included in that request.

Impact: Comp selection is not actually bound to the resolved subject location.

Required repair: Use a verified supported source contract with explicit subject geometry and radius; withhold when binding is absent.

Acceptance check: Captured provider requests and returned comp coordinates must match two distinct subjects.

Probe evidence: R08 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G14 — Social and eviction runners count unsaved results

**High · reproduced · Sophia**

Source: [backend/scout/social_scraper.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/social_scraper.py#L90)

Social and eviction runners return a count without durable candidate or canonical lead creation.

Impact: Discovery appears successful while Bob/Sophia receive nothing.

Required repair: Persist dated source candidates, verify parcel/address and idempotently create canonical leads without contact authority.

Acceptance check: Synthetic source result must be observable in the canonical database and dashboard, including retry.

Probe evidence: R09, R10 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G15 — Main scout cycle omits configured source runners

**High · reproduced · Sophia**

Source: [backend/scout/cron.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/cron.py#L156)

The API lifespan schedules run_scout_cycle, which runs RSS, expired and eviction only. The separate start_scheduler path includes CRMLS/social/CSV but is not the Railway start command.

Impact: Merged CRMLS persistence repair is not sufficient to make it run in the main deployment path.

Required repair: Define one explicit source registry and schedule with per-source durable outcomes.

Acceptance check: Boot the actual configured entry point and assert each enabled source is called and persisted.

Probe evidence: R11 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G16 — RSS source is empty and lacks operational coverage

**Medium · source_confirmed · Sophia**

Source: [backend/scout/rss_scraper.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/rss_scraper.py#L66)

RSS_FEEDS is an empty list; the module safely returns zero. Titles are currently assigned to address and every ZIP result is labeled Stockton.

Impact: No RSS leads are discovered; naive future activation would create unverified identities.

Required repair: Configure supported feeds and normalize source titles separately from verified property addresses.

Acceptance check: Source inventory must distinguish disabled, empty, failed, candidate and saved lead outcomes.

### G17 — Expired/FSBO property candidates do not create leads

**High · source_confirmed · Sophia**

Source: [backend/scout/expired.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/expired.py#L17)

The expired path saves through upsert_listing_candidate but does not perform the canonical lead creation used by persist_mls_candidate.

Impact: New property-only candidates remain invisible to Bob lead jobs.

Required repair: Route verified candidates through a shared canonical lead persistence service.

Acceptance check: New candidate yields exactly one property and lead; retries preserve reviewed fields.

### G18 — Automatic enrichment may receive property ID instead of lead ID

**High · source_confirmed · Sophia**

Source: [backend/scout/cron.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/scout/cron.py#L48)

After insert_lead returns lead_id, the enrichment branch chooses prop.lead_id or prop.id; the local property dictionary normally only has its property ID.

Impact: Enrichment fails or targets the wrong identity.

Required repair: Pass the returned canonical lead_id and validate binding before enrichment.

Acceptance check: A property ID distinct from its lead ID must never be passed as the lead argument.

### G19 — Lead insertion and reverse-link update are not atomic or retry-safe

**High · source_confirmed · Sophia**

Source: [backend/lib/db.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/lib/db.py#L61)

Lead insert and properties.lead_id update are separate operations; callers first read then insert, without a transaction or stable source-key contract.

Impact: Concurrent imports or acknowledgement loss can create duplicate leads or incomplete links.

Required repair: Use one tenant-bound atomic RPC with idempotent source/parcel keys.

Acceptance check: Independent database connections racing and crashing between insert/link updates.

### G20 — Legacy mutations can claim success on zero saved rows

**High · reproduced · Sophia**

Source: [backend/api/routes/leads.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/api/routes/leads.py#L125)

Notes and campaign pause return success when the adapter returns an empty update result. Similar patterns exist for activation, property state and followups.

Impact: Dashboard/operator believes an action completed when it did not.

Required repair: Require matching write receipts and apply explicit not-found/conflict/retryable errors everywhere.

Acceptance check: Empty, wrong-row, multiple-row and lost-ack tests across the mutation inventory.

Probe evidence: R12, R13 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G21 — Email unsubscribe acknowledges lost writes

**High · reproduced · Sophia**

Source: [backend/api/routes/email_webhook.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/api/routes/email_webhook.py#L212)

Database errors are swallowed by unsubscribe handlers; provider webhook returns 200 and link page says unsubscribed successfully.

Impact: Suppression can be lost and the provider will not necessarily retry.

Required repair: Persist address-wide suppression locally before acknowledgement and recover it; do not confirm unsaved results.

Acceptance check: Database outage, restart, signed duplicate events and all leads sharing the email.

Probe evidence: R17, R18 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G22 — Email adapter ignores disabled outbound and suppression

**High · reproduced · Sophia**

Source: [backend/alerts/email.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/email.py#L90)

With OUTBOUND_ENABLED=false a configured email adapter still issues a provider request and returns accepted. It does not itself check email-wide suppression or lead consent.

Impact: Disabling phone/tool actions does not necessarily stop marketing email.

Required repair: Centralize explicit channel-aware outbound control and durable email suppression, with separately authorized operational notifications.

Acceptance check: Direct sends, scheduled sends and buyer sends must deny disabled/suppressed contacts.

Probe evidence: R21 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G23 — Accepted SMS becomes failure after logging outage

**High · reproduced · Sophia**

Source: [backend/alerts/sms.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/sms.py#L39)

Provider returns a message SID, then insert_sms raises; the whole method returns False.

Impact: A retry can send twice and provider acceptance can disappear from local history.

Required repair: Use a durable outbound intent and provider-result reconciliation before retries.

Acceptance check: Lost provider acknowledgement and post-acceptance datastore outage with stable intent identity.

Probe evidence: R19 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G24 — Deal blast records failed channels as sent

**High · reproduced · Sophia**

Source: [backend/alerts/deal_blast.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/deal_blast.py#L7)

Both send adapters return False, yet sms_sent/email_sent are stored as true because the contact strings are nonempty.

Impact: Failed sends become successful records and future retries are suppressed.

Required repair: Persist actual per-channel outcome and receipt; distinguish pending, accepted, delivered, failed and unknown.

Acceptance check: One/both channel failures and retry after partial success.

Probe evidence: R20 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G25 — Deal blast send-before-log race allows duplicates

**High · risk · Sophia**

Source: [backend/alerts/deal_blast.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/deal_blast.py#L7)

Idempotency checks precede provider sends; the log is inserted afterward with no owned claim around the send.

Impact: Concurrent runs or a crash between send and log can duplicate outreach.

Required repair: Claim durable per-channel intents before sends and reconcile unknown acceptance.

Acceptance check: Two independent workers plus crash immediately after provider acceptance.

### G26 — Walkthrough email caller has incompatible arguments

**Medium · reproduced · Sophia**

Source: [backend/workflows/engine.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/workflows/engine.py#L46)

Workflow passes three objects to a function requiring four scalar arguments; signature binding raises TypeError. The workflow catches and logs it.

Impact: Booking confirmation email is skipped.

Required repair: Call the typed interface with canonical email/name/address and a formatted zoned appointment after verified reservation.

Acceptance check: Actual workflow booking branch must invoke the adapter once with correctly typed values.

Probe evidence: R16 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G27 — Completed walkthrough still triggers no-show reminder

**High · reproduced · Sophia**

Source: [backend/voice/appointment_scheduler.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/voice/appointment_scheduler.py#L48)

A lead with walkthrough_state=completed and a past confirmed appointment still sends the no-show followup. Completion is not checked in the processing branch.

Impact: Customers can receive inappropriate reschedule messages after a completed visit.

Required repair: Use one appointment lifecycle/version for booking, completion, cancellation and reminders.

Acceptance check: Complete/cancel/reschedule between selection and send; exact appointment-version claims.

Probe evidence: R22 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G28 — Email-only nurture cannot advance without SMS drip date

**High · reproduced · Sophia**

Source: [backend/alerts/email.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/email.py#L135)

A lead with email_day=0 and last email 40 days ago but no drip_started_at sends no next step because days_elapsed is always zero.

Impact: Email-only leads stall after the first message.

Required repair: Persist a separate email sequence anchor and durable per-step claim; use explicit absolute/relative schedule semantics.

Acceptance check: Email-only campaign advances days 0/7/21/45 without SMS state.

Probe evidence: R24 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G29 — Inbound email conversation is not wired

**High · source_confirmed · Sophia**

Source: [backend/alerts/email.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/email.py#L185)

handle_email_reply is defined, but no runtime caller or inbound-message route is registered; SendGrid event processing handles delivery/open/click/unsubscribe rather than reply content.

Impact: Sophia cannot be certified as holding email conversations from these paths.

Required repair: Connect authenticated inbound email parsing, canonical sender/thread binding, memory and approved reply delivery.

Acceptance check: Operator-controlled reply-to inbox thread roundtrip and spoofed/mismatched sender rejection.

### G30 — Speed-to-lead scheduled touches are memory-only

**High · risk · Sophia**

Source: [backend/alerts/speed_to_lead.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/alerts/speed_to_lead.py#L159)

Touches 2–5 are APScheduler date jobs using the default in-memory store; lead attempt flags do not reconstruct lost jobs at restart.

Impact: Restart loses future touches; multiple replicas can schedule the same lead.

Required repair: Persist source-owned touch intents with leases and restart recovery.

Acceptance check: Restart after first touch and race two scheduler replicas without duplicate or missing touches.

### G31 — Poison lead aborts dashboard refresh page

**High · reproduced · Sophia**

Source: [backend/karpathys/outbox.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/karpathys/outbox.py#L45)

One bad lead raises during a batch publish and skips the healthy lead that follows. The offset has already advanced for full pages.

Impact: Healthy leads after the failing row can stay unsynchronized across repeated page rotations.

Required repair: Isolate each lead failure and retain its retry identity; paginate independently of item success.

Acceptance check: Bad first/middle/last lead must not block any healthy record.

Probe evidence: R23 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G32 — InstantDM writes are unauthenticated and unsigned

**Critical · reproduced · Dashboard**

Source: [backend/api/routes/instantdm_webhook.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/instantdm_webhook.py#L12)

The actual router accepts an anonymous POST and creates a social lead; the application router adds no global authentication.

Impact: Anyone reaching the endpoint can inject leads and pollute business data.

Required repair: Require provider/service authentication, payload budgets, stable event IDs and replay/conflict receipts.

Acceptance check: Full application anonymous/bad-signature/replay/oversize rejection tests.

Probe evidence: D01 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G33 — Any long text containing a digit is labeled an address and hot lead

**Medium · reproduced · Dashboard**

Source: [backend/api/routes/instantdm_webhook.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/instantdm_webhook.py#L12)

I owe 1000 dollars is assigned address_detected and hot intent.

Impact: Non-address messages become apparent property/intent evidence.

Required repair: Keep extraction unverified until structured address and parcel review; avoid invented intent certainty.

Acceptance check: Debt amounts, dates, phone numbers, negations and actual addresses.

Probe evidence: D02 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G34 — InstantDM retries create duplicate social leads

**High · reproduced · Dashboard**

Source: [backend/api/routes/instantdm_webhook.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/instantdm_webhook.py#L12)

Posting the same event twice creates two records.

Impact: Provider replay and attacker spam inflate the lead pipeline.

Required repair: Persist a sender-bound event/source identity with atomic deduplication and conflicting replay rejection.

Acceptance check: Identical simultaneous deliveries create one record.

Probe evidence: D03 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G35 — Legacy dashboard writes have login but no write permission

**High · reproduced · Dashboard**

Source: [backend/api/routes/social.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/social.py#L74)

A reviewer can create a post with status=posted. Email drip, referral, social-lead and Reddit mutation routes use similarly authentication-only boundaries.

Impact: Read/review roles can mutate outreach and commercial state.

Required repair: Define and enforce domain write/manage permissions and actor attribution on every mutation route.

Acceptance check: Role-by-route matrix for admin/operator/reviewer, including creation, conversion, scan, deletion and financial changes.

Probe evidence: D04 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G36 — Social/email delivery state can be manufactured

**High · reproduced · Dashboard**

Source: [backend/api/routes/email_drip.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/email_drip.py#L97)

Advance sets last_sent_at without sending or a provider receipt; social create/update accepts posted status directly.

Impact: Dashboard status is not evidence of real delivery/publication.

Required repair: Separate manual status notes from provider-backed delivery events and durable intents.

Acceptance check: Missing/mismatched/duplicate provider receipts cannot advance actual delivery state.

Probe evidence: D05, D06 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G37 — Curator fetch permits private server URLs

**High · reproduced · Dashboard**

Source: [backend/api/routes/curator.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/curator.py#L39)

The fetch helper accepts a loopback URL and returns its content preview; it also follows redirects without destination controls. Only a mocked adapter was used.

Impact: Authenticated users can request internal services; redirect/DNS variants need verification.

Required repair: Allow supported public HTTPS destinations, reject private/reserved addresses before and after redirects, and bound streamed responses.

Acceptance check: Loopback/private/link-local, rebinding and redirect rejection plus allowed public cases.

Probe evidence: D10 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G38 — Missing-model fallback fabricates a recent closing

**Medium · reproduced · Dashboard**

Source: [backend/api/routes/curator.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/curator.py#L50)

Without the AI key, one generated fallback says the business just closed another house. No closing record supports it.

Impact: Unverified marketing claims can enter saved or posted content.

Required repair: Return unavailable or grounded generic drafts with source/provenance and review status.

Acceptance check: Missing key/provider failure must never create an event or deal claim.

Probe evidence: D11 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G39 — Manual source deduplication is scoped to actor

**Medium · reproduced · Dashboard**

Source: [backend/services/lead_creation.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/lead_creation.py#L11)

The same provider source record under two operators generates distinct create keys. This is a team deduplication discrepancy, not proof that intentional duplicate leads are forbidden.

Impact: Multiple operators can create duplicate property leads.

Required repair: Define global tenant/source/property identity with explicit intentional-duplicate rules.

Acceptance check: Two operators and two source channels for one parcel, including intentional duplicates.

Probe evidence: D08 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G40 — Soft-deleted leads remain available in detail/mutations

**High · reproduced · Dashboard**

Source: [backend/api/routes/leads.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/leads.py#L146)

List and business-evidence reads exclude deleted rows; detail and several mutation queries do not. The detail function returns a deleted fixture and its SQL lacks the predicate.

Impact: Deleted records can still be read or modified through direct IDs.

Required repair: Use the shared repository soft-delete contract for all endpoints and related timelines.

Acceptance check: Deleted lead detail, notes, status, followup and timeline all reject.

Probe evidence: D07 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G41 — Refresh token rotation is not atomic

**High · reproduced · Dashboard**

Source: [backend/api/routes/auth.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/auth.py#L98)

Two concurrent calls using the same real signed refresh token both pass the separate blacklist check and each returns a new token pair under a synchronized fake Redis adapter.

Impact: A replay race creates multiple valid successor refresh tokens.

Required repair: Atomically claim the refresh JTI once and maintain revocable token families.

Acceptance check: Independent Redis/client concurrency with exactly one accepted successor; crash/retry behavior defined.

Probe evidence: D12 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G42 — Logout revokes access token but not refresh family

**High · source_confirmed · Dashboard**

Source: [backend/api/routes/auth.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/api/routes/auth.py#L129)

Logout blacklists the current access JTI; it receives/revokes no refresh token or session family. Refresh does not look up current user status before minting successors. Current access checks still read the user, so this is not proof of role escalation.

Impact: A retained refresh credential can mint tokens after logout until expiry.

Required repair: Revoke the session refresh family at logout and recheck account status at refresh.

Acceptance check: Retained refresh token after logout/password reset/account suspension must fail.

### G43 — Legacy malformed business snapshot causes read failure

**Medium · reproduced · Dashboard**

Source: [backend/services/business_evidence.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/business_evidence.py#L124)

A previously persisted valuation without as_of raises KeyError on read. Earlier validation accepted valuation dictionaries without that date.

Impact: Existing records from the older schema can make the evidence panel fail after an upgrade.

Required repair: Version/validate old snapshots on reads and return an explicit unavailable/review state; migrate deliberately.

Acceptance check: Old missing/invalid date, timezone and collection shapes never cause 500.

Probe evidence: D09 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G44 — Valuation ingest accepts comps without price or closed date

**High · reproduced · Dashboard**

Source: [backend/services/business_evidence.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/business_evidence.py#L12)

Three distinct sale IDs and source refs with null sale prices, null adjusted values and no closed dates pass as ready advisory evidence.

Impact: A ready-looking valuation can have no concrete displayed sale-price/date evidence. Producer-side checks reduce current exposure but do not complete receiver validation.

Required repair: Require complete comparable identity, dated closed status, positive cents and reviewed lineage for a ready valuation.

Acceptance check: Missing, future, stale, duplicate and wrong-property comp evidence must withhold ready status.

Probe evidence: D13 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G45 — Existing external lead mapping never refreshes missing contacts

**High · reproduced · Dashboard**

Source: [backend/services/voice_ingest.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/voice_ingest.py#L60)

An existing Unverified seller row with no phone remains unchanged when a later mapped event carries a source name and phone. Business snapshots do not carry phone/email.

Impact: Pre-call imports can leave dashboard contact/name data incomplete even after calls.

Required repair: Reconcile source-bound contact fields with timestamps and conflict rules, preserving reviewed operator edits.

Acceptance check: Business-before-call and call-before-business converge on the same reviewed contact data.

Probe evidence: D14 in [the machine-readable ledger](FORENSIC-GAPS-20261014.json).

### G46 — Operational lead/calendar/deal state is not fully synchronized

**High · source_confirmed · Dashboard**

Source: [backend/services/business_evidence.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/services/business_evidence.py#L76)

Business ingestion stores snapshots and address labels, not source stage, followup_at, assigned operator or a local Property entity. Calendar reads Lead.follow_up_at; deals reads qualified/converted local status. Local manual creation does not emit a canonical REI lead.

Impact: The evidence panel works while calendar/deal pipeline and actions remain separate systems.

Required repair: Specify authoritative fields and governed state transitions; connect source bookings/followups and operator actions with bidirectional receipts.

Acceptance check: One reviewed lead through creation, valuation, authorized contact, reservation, completion and deal state across both databases.

### G47 — Development admin seeding contains a fixed credential

**High · source_confirmed · Dashboard**

Source: [backend/scripts/seed_admin.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/scripts/seed_admin.py#L14)

The seed script hashes a hardcoded password for a hardcoded administrator, without a production guard. Credential values are intentionally omitted from this report.

Impact: A database provisioned with this script can have a predictable admin login; actual deployment use is unknown.

Required repair: Require explicit secure credential input or one-time generated setup; forbid dev seeding in production.

Acceptance check: No fixed credential exists in the supported production bootstrap; validate an existing seeded account safely.

### G48 — Bootstrap is platform-specific and advertises the wrong password

**Medium · source_confirmed · Dashboard**

Source: [scripts/dev/bootstrap.sh](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/scripts/dev/bootstrap.sh)

The script hardcodes a versioned Homebrew PostgreSQL path and prints a login password different from seed_admin.py. It also uses the legacy migration bootstrap path.

Impact: Setup fails on other platforms and the printed login fails; fresh-schema path consistency needs verification.

Required repair: Use portable executables and the canonical initialization command; never advertise a static password.

Acceptance check: Clean Linux/macOS setup and actual generated login with one supported schema head.

### G49 — Rate limiting module is empty

**Medium · source_confirmed · Dashboard**

Source: [backend/security/rate_limits.py](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/backend/security/rate_limits.py)

The module has zero lines; login and public lead webhook have no application rate-limit integration in the inspected routes. External edge controls were not accessible.

Impact: Credential guessing, lead injection and paid-provider request amplification are not constrained here.

Required repair: Add bounded account/IP/service event budgets and document edge limits.

Acceptance check: Burst/concurrent requests and degraded Redis behavior, without blocking legitimate STOP/recovery.

### G50 — Synchronous database calls block async legacy routes

**Medium · source_confirmed · Sophia**

Source: [backend/api/routes/leads.py](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/backend/api/routes/leads.py#L16)

Legacy async endpoints call synchronous Supabase execute and some scraper/comp work directly; the newer offer routes use the threadpool.

Impact: Slow datastore/provider work can delay other requests in the same process.

Required repair: Centralize bounded async/threadpool adapters and isolate long scouting work from the voice/webhook process.

Acceptance check: Concurrent delayed requests must not stall health, STOP, callbacks or voice control.

### G51 — Shared REI/Bob clean baseline is incomplete

**High · source_confirmed · Sophia**

Source: [supabase/migrations/20260911_tenant_and_suppression.sql](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/supabase/migrations/20260911_tenant_and_suppression.sql)

Migration explicitly skips business tables that do not exist; core leads/properties/contacts schemas are not created in the inspected committed migration set. Bob SQL harness supplies a minimal scaffold.

Impact: A clean shared deployment or independent upgrade cannot be certified from existing contract tests alone.

Required repair: Reconstruct and verify the authoritative frozen shared baseline, upgrade paths and RLS/RPC grants.

Acceptance check: Empty database plus representative legacy copy, independent connections and full PostgREST queries.

### G52 — Old audit summaries conflict with merged state

**Medium · source_confirmed · Sophia**

Source: [docs/system-audit/MASTER-ISSUES.md](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/docs/system-audit/MASTER-ISSUES.md)

Historical summaries still say nothing merged and retain old test counts/open items; later repairs and current merged heads are documented elsewhere.

Impact: Operators can confuse old findings, repaired defects and current release gates.

Required repair: Maintain a current head-bound ledger that preserves but clearly labels historical evidence.

Acceptance check: Every closed finding names its exact fix and verification; no blanket historical statement overrides current source.

### G53 — Current San Joaquin sold-data acceptance is missing

**High · blocked · Bob**

Source: [docs/VALUATION-MODEL-RESEARCH-AND-GRADE.md](https://github.com/Lavish213/Bob-Intelligence-/blob/44059af6766811add52cf7849dda7ea36e8e164c/docs/VALUATION-MODEL-RESEARCH-AND-GRADE.md)

The research benchmark is historical Ames/Iowa data and a repeatedly examined cohort. Current local closed-sale and renovation-scope acceptance was not available.

Impact: The tested math and Iowa error rate do not establish current Stockton/Lodi ARV accuracy.

Required repair: Acquire permitted current sold/condition data and seal independent local/temporal cohorts; retain severe misses.

Acceptance check: Segmented local sale/ARV errors, coverage, severe-tail audit and reviewed source authenticity.

### G54 — Public county candidate evidence is not deal underwriting

**High · blocked · Bob**

Source: [docs/SAN-JOAQUIN-LEAD-SAMPLE-20261014.json](https://github.com/Lavish213/Bob-Intelligence-/blob/44059af6766811add52cf7849dda7ea36e8e164c/docs/SAN-JOAQUIN-LEAD-SAMPLE-20261014.json)

County sample contains candidates with arv_cents unset; parcel context and tax notice matches do not supply a reviewed sale-price/condition/repair/offer package.

Impact: Candidate discovery cannot be equated with a verified profitable deal.

Required repair: Build dated per-property reviewed comps, condition, repairs, costs/title and explicit offer authority.

Acceptance check: Blind property-level underwriting against reviewed actual outcomes and evidence receipts.

### G55 — Queue quarantine and evidence expiration require operations ownership

**High · risk · Bob**

Source: [backend/worker/loop.py](https://github.com/Lavish213/Bob-Intelligence-/blob/44059af6766811add52cf7849dda7ea36e8e164c/backend/worker/loop.py#L22)

Worker and event failures log/back off; quarantined jobs, expired feedback and dead events require deliberate operator recovery. Configured alert/backup ownership was not accessible.

Impact: The system can be safe but silently stop useful processing if nobody handles degraded queues.

Required repair: Assign and surface queue age, quarantine/dead-letter alerts, recovery procedures and backup ownership.

Acceptance check: Observed alerts and owned recovery for worker kill, repeated source error, outage and restored volume.

### G56 — Production/provider end-to-end acceptance is not available

**High · blocked · Dashboard**

Source: [docs/END-TO-END-BUSINESS-EVIDENCE.md](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/docs/END-TO-END-BUSINESS-EVIDENCE.md)

CI verifies synthetic source data and real disposable PostgreSQL/HTTP, not the deployed accounts, providers or actual operator calendar.

Impact: Live phone quality, SMS/email delivery, permissions, scheduling and rollout remain unproven.

Required repair: Connect approved staging/deployment/provider accounts and use designated test recipients and disposable records.

Acceptance check: Exact deployed commit, real bidirectional call/message/calendar roundtrip and rollback evidence.

### G57 — Persistent volume and multi-replica behavior is unverified

**High · blocked · Sophia**

Source: [docs/BOB-RECOVERY-REAUDIT.md](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/docs/BOB-RECOVERY-REAUDIT.md)

Suppression, facts and dashboard delivery use local private SQLite journals. Production volume durability, shared replica ownership and restore behavior were not accessible.

Impact: A lost or separate replica volume can lose pending state or delay suppression visibility.

Required repair: Verify the configured topology and persistence contracts; test restore and cross-process suppression.

Acceptance check: Kill/redeploy/two-replica/outage/restore drills with no duplicate communication and no suppressed-contact send.

### G58 — Real voice quality and conversations are not measured

**High · blocked · Sophia**

Source: [docs/system-audit/CALIFORNIA-VOICE-ACCEPTANCE.md](https://github.com/Lavish213/REI-AGENT/blob/0ae65ff799eb1c54aad846f9a76ca35c1b7e2263/docs/system-audit/CALIFORNIA-VOICE-ACCEPTANCE.md)

Text/logic tests do not measure actual ASR errors, noise, accents, interruption, latency, language switching or spoken unsupported promises.

Impact: A high unit-test count cannot justify a 10/10 conversational grade.

Required repair: Build a consented operator-controlled audio corpus and independent human grading with explicit failure thresholds.

Acceptance check: Real turn/audio/latency metrics and severe-error review through provider outages and handoff.

### G59 — Legacy production migration and rollback remain unproven

**High · blocked · Dashboard**

Source: [docs/database/AUDIT_TABLES.md](https://github.com/Lavish213/The-Dashboard/blob/4b8c556c94d15de55dbc1a0ad68b18f5d19912d5/docs/database/AUDIT_TABLES.md)

Fresh disposable schema tests do not establish upgrades and rollback on the existing production database. No live migration was performed in this audit.

Impact: Deployment can fail despite a green fresh-install test.

Required repair: Rehearse upgrades on a backed-up sanitized representative database and verify rollback/data retention.

Acceptance check: Pre/post schema, row invariants, RLS/API queries and restore/rollback evidence.

## Repeatable isolated probes

Install the repositories’ declared runtime dependencies in isolated environments. The two scripts are audit counterexample runners, not passing regression suites. They report observed behavior and required behavior. No network request or live write is needed.

```sh
cd /path/to/REI-AGENT
PYTHONPATH=. python /path/to/The-Dashboard/scripts/audit_rei_gap_probes.py
cd /path/to/The-Dashboard
PYTHONPATH=backend python scripts/audit_dashboard_gap_probes.py
```

The JSON result includes probe limits. Capture stdout as JSON; logging is emitted separately. Resolve each case by writing an independent regression for the required behavior, repairing it, and retesting the actual integration boundary.

## Source coverage and operating prerequisites

The API’s scout cycle currently differs from the standalone scheduler. CRMLS support/persistence exists, but the API cycle does not invoke it. RSS has no configured feeds. Social and eviction results are not persisted. Expired property candidates lack the canonical lead step. CSV requires actual input files and uses a separate entry path. A court/tax module existing in the repository does not prove its source login, current parsing contract, scheduler integration or end-to-end lead persistence.

Required settings and evidence include the same Supabase project/schema/tenant, Bob and Sophia tenant IDs, explicit enabled background jobs, persistent private journal paths, configured dashboard webhook destination/secret, provider signing keys/public HTTPS URL, approved current contact permissions, reviewed price grants and actual availability slots. Missing prerequisites should produce a visible blocked state. They should never be bypassed to improve a grade.

The calendar currently shows local lead followups, not a verified external calendar. Deals currently depend on local qualified/converted status. Recorded offer, social and email status must be distinguished from actual provider outcomes.

## Already-fixed or unproven issues were not inflated into new bugs

- Bob job seeding excludes existing jobs before its 1000-row batch limit; the inspected limit does not establish permanent top-1000 starvation.
- Current dashboard websocket code revalidates identity/role; old summaries saying that remains open are not treated as a new defect.
- OUTBOUND_ENABLED and action grants intentionally deny unsafe calls; unavailable credentials/consent/slots are operating prerequisites, not reasons to bypass those checks.

The prior green suites remain useful regression evidence for their exact source heads. The newly reproduced defects show that those suites did not establish complete acceptance of every legacy module. No A or autonomous production-ready grade is justified until the release stops and live acceptance gates above close.

## Remediation follow-up

PRs [Sophia #9](https://github.com/Lavish213/REI-AGENT/pull/9) and [Dashboard #7](https://github.com/Lavish213/The-Dashboard/pull/7) implement the current lockdown. The historical findings and probes above remain evidence of the original behavior, not current passing tests. See the JSON remediation section and Sophia docs/FORENSIC-LOCKDOWN.md for implemented, contained and still-open work. No live provider, production upgrade or current San Joaquin valuation acceptance is claimed. Initial CI passed Sophia and the dashboard backend; final revisions require exact-head checks before merge.
