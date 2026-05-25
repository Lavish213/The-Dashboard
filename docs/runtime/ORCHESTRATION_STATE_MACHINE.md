# ORCHESTRATION_STATE_MACHINE

## Purpose

Defines the deterministic orchestration lifecycle for all execution graphs and orchestration-controlled runtime flows.

This document is canonical runtime law for:
- orchestration states
- valid transitions
- recovery semantics
- replay semantics
- cancellation behavior
- governance pauses
- dead-letter routing
- terminal state guarantees

All orchestration behavior must conform to this state machine.

---

# Core Doctrine

Orchestration state must always be:
- explicit
- auditable
- deterministic
- replay-safe
- recoverable
- append-only event driven

Hidden state transitions are forbidden.

Implicit transitions are forbidden.

---

# Orchestration Unit

An orchestration unit is a managed execution flow containing:
- execution graph
- runtime state
- checkpoints
- audit events
- governance state
- budget tracking
- recovery metadata

Each orchestration unit owns exactly one authoritative lifecycle state.

---

# Authoritative States

Allowed orchestration states:

```text id="lup9s7"
created
validating
queued
running
paused
waiting_approval
checkpointed
retrying
recovering
completed
failed
cancelled
dead_lettered