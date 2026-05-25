# AGENT_CONTRACTS

## Purpose

Defines the deterministic contract boundary for all orchestration agents.

This document is the canonical runtime law for:
- agent capabilities
- execution boundaries
- orchestration guarantees
- governance compatibility
- replay determinism
- failure containment
- audit enforcement
- tool permissions
- memory boundaries
- lifecycle semantics

Agents are execution units.

Agents are NOT autonomous entities.

This document is production-authoritative.

---

# Core Doctrine

## Deterministic First

All agent behavior must remain:
- replayable
- auditable
- bounded
- checkpointable
- cancellation-safe
- governance-compatible
- failure-isolated
- observable

No agent may:
- mutate hidden global state
- self-spawn recursively
- bypass orchestration
- bypass governance
- execute hidden side effects
- retain uncontrolled memory
- silently escalate permissions
- execute non-audited actions
- persist unauthorized state

---

# Runtime Philosophy

The orchestration layer is authoritative.

Agents are workers.

Governance is mandatory.

Auditability is permanent.

Human oversight is final.

The system is designed for:
- deterministic orchestration
- bounded intelligence
- replay-safe execution
- production governance
- recoverable workflows
- observable runtime behavior

Agents are intentionally constrained.

---

# Agent Definition

An agent is a deterministic execution worker that:

1. receives structured input
2. executes within explicit constraints
3. produces structured output
4. emits append-only events
5. supports replay/recovery semantics
6. obeys governance enforcement
7. remains fully auditable

Agents are orchestration-controlled.

Agents do not control orchestration.

---

# Required Agent Properties

Every agent MUST define:

```python
agent_id
agent_type
agent_version
input_contract
output_contract
execution_budget
timeout_budget
retry_policy
governance_policy
capability_scope
allowed_tools
blocked_tools
checkpoint_policy
cancellation_policy
observability_policy