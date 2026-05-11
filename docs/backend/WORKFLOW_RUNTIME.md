# Karpathys Platform — Workflow Runtime Canon

Status: LOCKED
Authority Level: TIER 0
Last Updated: 2026-05
Overrides: All workflow/orchestration documents

---

# Purpose

The workflow runtime is the operational brain of Karpathys.

It coordinates:
- operational state
- execution sequencing
- approvals
- retries
- escalations
- recovery
- orchestration
- persistence
- event emission

The workflow runtime is authoritative.

No subsystem may bypass it.

---

# Workflow Philosophy

Karpathys workflows are:
- deterministic
- resumable
- replayable
- inspectable
- auditable
- event-driven
- failure-aware

Workflows are NOT:
- hidden async jobs
- uncontrolled agent loops
- fire-and-forget tasks
- invisible background processes

Every important operation must exist inside workflow execution.

---

# Golden Doctrine

## Every Workflow Has

- a unique identity
- a canonical state
- a lifecycle
- event history
- retry semantics
- escalation semantics
- auditability
- persistence
- ownership
- recovery capability

---

# Workflow Hierarchy

```text
Workflow Definition
    ↓
Workflow Instance
    ↓
Workflow State Machine
    ↓
Workflow Events
    ↓
Workflow Tasks
    ↓
Workflow Effects