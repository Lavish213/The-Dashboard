# End-to-end business evidence acceptance

This repair closes the reproduced 405 on property-search lead creation, persists eligible MLS candidates, and adds a durable, read-only business-data bridge to Karpathys.

## Concrete paths

- Property search POST /api/v1/leads requires authenticated LEADS_READ and LEADS_WRITE, bounded typed fields and source_record_id. It preserves address/city/state, records the operator, does not manufacture a score, and serializes retry handling with a PostgreSQL advisory lock. Identical retries return the existing lead; conflicting/deleted source records reject.
- REI MLS candidates require a canonical eight-digit parcel, explicit county/state and address before persistence. Existing reviewed property fields are preserved. A deterministic import lead ID prevents duplicate inserts from simultaneous retries. Imported leads start non-callable. Asking prices stay separate from ARV; missing APNs are withheld for enrichment, not replaced by listing IDs.
- REI builds a canonical same-lead/property snapshot through backend/lib/db.py. Current Bob briefs provide reviewed advisory prices and accepted-comparable source/price detail. Offers retain their actual draft/sent/countered/accepted/rejected/expired status. Appointments retain their actual recorded time/status, including cancellation. No snapshot grants contact or offer authority.
- Business snapshots use content revisions with hourly observation refreshes and seven-day bounded receipt retention and the existing durable outbox. They can create an external lead mapping before any call without inventing a call. Call-associated snapshots additionally verify the provider-call/lead mapping. Receipts survive lost acknowledgements; old observations cannot reinstate a superseded appointment. Property rebindings fail for review. New updates enqueue at call start and after tools; the recovery worker backfills 100 lead records per minute in rotating pages.
- Karpathys stores business evidence on its existing lead metadata; no schema migration is needed for this projection. An authenticated read route and lead-detail panel show source APN, reviewed value/range/date, comp source references and prices, recorded offer status/amount/repairs, source appointment time/status, and explicit loading, unavailable, error and stale states. This does not create a separate booking authority or synchronize contact permission.

## Verification requirements

CI runs all backend database tests and Ruff, manual lead creation/retry/role checks, business snapshot binding/replay/old-date tests, actual pinned Bob valuation → REI snapshot → real HTTP → PostgreSQL persistence, and the existing outbox restart/pre-write-outage/post-commit-acknowledgement-loss checks. Frontend checks include type/lint/build and a rendered business-evidence state with assertions for correct cents and draft status. Source commits are pinned explicitly in workflow.

## Live acceptance still requires actual access

No production provider secrets are available in this workspace. A green source/CI run cannot demonstrate production migrations/volumes, licensed MLS endpoint access, current local sold comps and inspection scope, external calendar availability, delivered SMS/email, real STT/LLM/TTS conversation quality or actual phone latency. No seller communications or paid data requests occurred. Fixture comparisons and draft offers are labelled as such. Deployment must configure persistent outbox/suppression storage and the authenticated target before transport can run.
