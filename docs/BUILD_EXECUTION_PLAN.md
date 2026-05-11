# Karpathys Platform — Build Execution Plan

Status: LOCKED
Authority Level: EXECUTION CANON

---

# Purpose

This document defines:
- build order
- phase sequencing
- implementation boundaries
- dependency ordering
- execution gates
- Warp execution constraints

The platform must be built deterministically.

No uncontrolled implementation allowed.

---

# Global Doctrine

Rules:
1. Never skip phases.
2. Never bypass foundations.
3. Never build upward before lower layers stabilize.
4. Never modify unrelated systems during a phase.
5. Every phase must pass validation before next phase.
6. Warp must obey doctrine documents.
7. No speculative refactors.
8. No architecture invention.
9. No hidden state systems.
10. No parallel conflicting implementations.

---

# Phase 0 — Foundation Lock

## Purpose

Stabilize tooling and project structure.

---

## Allowed

- package setup
- workspace config
- tsconfig
- eslint
- prettier
- env setup
- aliases
- docker
- repo validation

---

## Forbidden

- business logic
- workflows
- realtime
- AI
- transcript rendering

---

## Exit Conditions

- imports resolve
- lint passes
- typecheck passes
- folders validated
- aliases validated
- docker boots
- backend boots
- frontend boots

---

# Phase 1 — Design System

## Purpose

Build visual primitives and UI foundation.

---

## Allowed

- tokens
- typography
- themes
- spacing
- dark mode
- ui primitives
- accessibility base
- motion primitives

---

## Forbidden

- workflows
- transcript systems
- realtime logic
- backend APIs

---

## Exit Conditions

- visual tokens stable
- accessibility validated
- dark mode stable
- primitives reusable
- responsive primitives functional

---

# Phase 2 — App Shell

## Purpose

Build operational application shell.

---

## Allowed

- routing
- layouts
- navigation
- providers
- auth shell
- command palette
- responsive shell

---

## Forbidden

- workflow logic
- AI runtime
- realtime events
- transcript streaming

---

## Exit Conditions

- routing stable
- layouts responsive
- navigation operational
- keyboard navigation functional
- shell accessible

---

# Phase 3 — Backend Core

## Purpose

Build deterministic backend runtime.

---

## Allowed

- postgres models
- migrations
- repositories
- auth
- RBAC
- workflow persistence
- event persistence
- observability base

---

## Forbidden

- AI orchestration
- transcript intelligence
- advanced realtime UI

---

## Exit Conditions

- migrations stable
- repositories functional
- RBAC validated
- audit logging functional
- event persistence functional

---

# Phase 4 — Realtime Runtime

## Purpose

Build operational synchronization systems.

---

## Allowed

- websocket runtime
- subscriptions
- replay
- reconnect
- cache reconciliation
- optimistic systems

---

## Forbidden

- AI orchestration
- transcript intelligence overlays

---

## Exit Conditions

- replay functional
- reconnect stable
- stale reconciliation functional
- optimistic rollback functional

---

# Phase 5 — Workflow Runtime

## Purpose

Build orchestration engine.

---

## Allowed

- workflow states
- transitions
- retries
- escalation
- approvals
- compensation
- rollback

---

## Forbidden

- advanced AI execution

---

## Exit Conditions

- workflows replayable
- retries deterministic
- approvals functional
- rollback validated

---

# Phase 6 — Transcript System

## Purpose

Build transcript intelligence runtime.

---

## Allowed

- transcript rendering
- streaming
- virtualization
- playback
- transcript indexing
- transcript search

---

## Forbidden

- autonomous AI actions

---

## Exit Conditions

- transcript streaming stable
- virtualization functional
- replay stable
- transcript search functional

---

# Phase 7 — Approval System

## Purpose

Build governance systems.

---

## Allowed

- approval queues
- risk displays
- approval actions
- escalation UI
- audit rails

---

## Exit Conditions

- approvals replayable
- auditability validated
- escalation stable

---

# Phase 8 — AI Runtime

## Purpose

Build AI assistance layer.

---

## Allowed

- summaries
- recommendations
- extraction
- AI reasoning
- AI insights
- governance enforcement

---

## Forbidden

- hidden mutations
- unauthorized workflow control

---

## Exit Conditions

- AI traceability functional
- AI auditability functional
- AI permissions enforced

---

# Phase 9 — Mobile Runtime

## Purpose

Operational mobile execution.

---

## Allowed

- gestures
- mobile navigation
- offline handling
- reconnect recovery
- responsive workflows

---

## Exit Conditions

- mobile workflows functional
- mobile reconnect stable
- safe areas validated

---

# Phase 10 — Hardening

## Purpose

Production stabilization.

---

## Allowed

- testing
- observability
- replay simulation
- load testing
- accessibility audit
- security hardening

---

## Exit Conditions

- production stability validated
- replay validated
- reconnect validated
- accessibility validated
- observability validated

---

# Global Build Gates

Before ANY phase completes:

Required:
- lint passes
- typecheck passes
- imports verified
- no duplicate systems
- no architecture drift
- no orphan components
- no hidden state ownership

---

# Final Doctrine

Karpathys must be built:
- deterministically
- incrementally
- auditably
- phase-by-phase
- without architectural drift

Execution discipline is mandatory.