# Offer and evidence integrity repair — 2026-10-14

This pass fixes confirmed defects discovered after the previous coordinated merges. It does not certify production or local valuation accuracy.

| Boundary | Confirmed defect | Repair |
|---|---|---|
| Sophia canonical property reader | Loaded the reverse properties.lead_id relationship rather than the lead's property_id | Load the property by the canonical foreign-key value and reject property/lead tenant disagreement |
| Operator offers | Caller-selected property could provide another house's ARV; coercible, negative or unbounded money accepted | Require canonical lead/property/configured tenant binding; strict bounded integer cents; nonnegative default screening offer |
| Actor attribution | Client controlled created_by | Derive actor from authenticated operator; shared operator token is recorded as operator |
| Offer persistence | Missing status receipt or absent creation readback could be reported as success | Require matching saved record; unconfirmed updates/readbacks return an error |
| API execution | Synchronous datastore requests ran on async request loop | Offload datastore calls to the threadpool |
| Dashboard valuation | Recently delivered snapshots could contain expired valuation dates or unmatched/duplicate comp counts | Validate current valuation date and distinct matching comps on ingestion; mark valuations stale when they expire after ingestion |
| Appointment snapshot | Unzoned or missing confirmed booking time accepted | Require a UTC offset and a time for confirmed/scheduled records |
| Ordering | Different snapshots at exactly the same observation timestamp overwrote one another | Reject timestamp conflicts for explicit review |
| UI polling | Refresh requests could overlap and resolve out of order | Permit one pending request; ignore responses after component cleanup |

Validation includes Bob's existing full Python regression suite, new independent Sophia offer-integrity cases, SQL-backed dashboard endpoint failures, stale read checks, and execution of the actual TypeScript component's polling effect with delayed responses. Coordinated CI also runs the real pinned Bob → Sophia → HTTP → PostgreSQL replay/restart test and browser checks. Inspect the final PR checks for exact commit evidence; local checks alone are not a release certification.

## Remaining live verification

No seller was called or messaged, offer sent, database migration applied, or hosting deployment initiated in this pass. Supabase, Railway, Vercel, phone/email/calendar providers and current licensed comparable-sales access remain required for production verification. Shared-token actor attribution cannot identify a particular person; use individual operator accounts when that distinction matters. A recorded offer status is not proof that a communication was delivered. The screening MAO is a heuristic and does not replace Bob's itemized project-cost analysis or a reviewed property valuation.

The canonical shared reader is repaired here. Legacy direct reverse-relationship queries in other REI modules still require a separately tested data-access consolidation; this pass does not claim that all historical modules or production migrations are complete.
