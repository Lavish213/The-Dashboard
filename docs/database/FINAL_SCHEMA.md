# Karpathys Platform — Final Schema Canon

Status: LOCKED
Authority Level: TIER 1

---

# Core Doctrine

Postgres is authoritative.

All entities use:
- UUID primary keys
- created_at
- updated_at
- status
- metadata jsonb

Soft deletes preferred.

All important mutations emit events.

---

# Core Entities

## users

Purpose:
Operators, admins, reviewers.

Core fields:
- id
- email
- role
- status
- last_active_at

---

## leads

Purpose:
Seller/contact lifecycle.

Core fields:
- id
- full_name
- phone
- email
- lead_status
- lead_source
- assigned_user_id
- property_id
- ai_score
- last_contacted_at

Indexes:
- phone
- assigned_user_id
- lead_status

---

## properties

Purpose:
Real estate entities.

Core fields:
- id
- address
- city
- state
- zip
- latitude
- longitude
- estimated_value
- property_status

Indexes:
- city/state
- geospatial
- property_status

---

## workflows

Purpose:
Operational orchestration runtime.

Core fields:
- id
- workflow_type
- workflow_status
- current_step
- correlation_id
- initiated_by
- expires_at

Indexes:
- workflow_status
- workflow_type
- correlation_id

---

## workflow_events

Purpose:
Immutable operational history.

Core fields:
- id
- workflow_id
- event_type
- payload jsonb
- causation_id
- correlation_id
- actor_type
- actor_id

Indexes:
- workflow_id
- correlation_id
- event_type
- created_at

---

## approvals

Purpose:
Human governance gates.

Core fields:
- id
- workflow_id
- approval_type
- approval_status
- requested_by
- resolved_by
- expires_at
- risk_level

Indexes:
- approval_status
- workflow_id

---

## transcripts

Purpose:
Call/session intelligence container.

Core fields:
- id
- lead_id
- workflow_id
- call_id
- transcript_status
- summary
- duration_seconds

Indexes:
- lead_id
- workflow_id
- created_at

---

## transcript_segments

Purpose:
Streaming transcript units.

Core fields:
- id
- transcript_id
- speaker
- text
- start_ms
- end_ms
- sentiment
- emotion

Indexes:
- transcript_id
- speaker
- start_ms

---

## calls

Purpose:
Voice runtime sessions.

Core fields:
- id
- lead_id
- workflow_id
- provider
- call_status
- started_at
- ended_at
- recording_url

Indexes:
- lead_id
- workflow_id
- call_status

---

## ai_decisions

Purpose:
AI reasoning/audit trail.

Core fields:
- id
- workflow_id
- transcript_id
- decision_type
- confidence
- reasoning
- model_name

Indexes:
- workflow_id
- decision_type

---

## realtime_sessions

Purpose:
Presence/realtime lifecycle.

Core fields:
- id
- user_id
- socket_id
- session_status
- connected_at
- disconnected_at

Indexes:
- user_id
- session_status

---

## notifications

Purpose:
Operational alerts.

Core fields:
- id
- user_id
- notification_type
- title
- body
- read_at

Indexes:
- user_id
- read_at

---

## audit_logs

Purpose:
Immutable operational auditing.

Core fields:
- id
- actor_id
- actor_type
- action
- target_type
- target_id
- metadata jsonb

Indexes:
- actor_id
- target_type
- target_id

---

# Relationship Doctrine

## leads
belongs_to:
- properties
- assigned users

has_many:
- workflows
- calls
- transcripts

---

## workflows
belongs_to:
- leads

has_many:
- workflow_events
- approvals
- ai_decisions

---

## transcripts
belongs_to:
- leads
- workflows
- calls

has_many:
- transcript_segments

---

## approvals
belongs_to:
- workflows

---

# Event Doctrine

Every important mutation creates:
- workflow event
- audit log

Critical operations also create:
- notification
- escalation
- realtime broadcast

---

# Index Doctrine

Required:
- all foreign keys
- created_at
- workflow_status
- approval_status
- transcript_id
- correlation_id

---

# JSONB Doctrine

Allowed ONLY for:
- metadata
- AI structured output
- replay context
- provider payloads

Canonical operational fields must remain relational.

---

# UUID Doctrine

All primary keys:
```text
uuid v4