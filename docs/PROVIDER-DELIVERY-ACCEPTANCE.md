# Provider delivery evidence

Source review includes authenticated provider delivery receipts from canonical REI/Sophia. `/api/v1/source-review/delivery` requires lead-read permission and authenticates to `/api/operations/delivery`. The proxy validates source tenant, exact schema version, bounded list, message identities, statuses, counters and Boolean flags, and strips recipients and raw payloads. Errors remain unavailable, not empty successful results.

The UI separates delivered/failed/conflicting evidence from open/click observations and address suppression. It reports pending events and warns that the read model may be incomplete until recovery succeeds. The latest 100 messages with callbacks are not a complete inventory of accepted sends. No receipt proves human reading or offer acceptance. Browser acceptance covers conflict/recovery, empty and unavailable states alongside existing connection and workflow views.

Requires source migration `20261020_provider_delivery_receipts.sql`, private persistent communication storage, signed callbacks and the source recovery loop. Deployed backend/database/provider operations still need verification. These changes do not establish production delivery, external calendar booking, audio quality, or San Joaquin valuation accuracy.
