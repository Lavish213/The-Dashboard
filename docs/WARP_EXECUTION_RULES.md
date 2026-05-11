# Karpathys Platform — Warp Execution Rules

Status: LOCKED
Authority Level: EXECUTION GOVERNANCE

---

# Purpose

This document governs all Warp implementation behavior.

Warp is an implementation worker.

Warp is NOT:
- architecture authority
- product designer
- system planner
- workflow inventor

Warp must obey doctrine documents.

---

# Absolute Rules

1. Never invent architecture.
2. Never rename canonical files.
3. Never bypass workflow doctrine.
4. Never bypass event contracts.
5. Never create hidden state systems.
6. Never create duplicate runtimes.
7. Never add dependencies without approval.
8. Never modify unrelated systems.
9. Never perform speculative refactors.
10. Never continue past failed validation.

---

# Doctrine Hierarchy

Highest authority:
1. BACKEND_ARCHITECTURE.md
2. FRONTEND_ARCHITECTURE.md
3. DESIGN_SYSTEM.md
4. EVENT_CONTRACTS.md
5. WORKFLOW_RUNTIME.md

Lower docs inherit from higher docs.

Higher-tier doctrine overrides lower-tier implementation.

---

# Phase Isolation Rules

Warp may ONLY modify files relevant to current phase.

Forbidden:
- touching future systems
- premature optimization
- cross-phase implementation
- hidden scaffolding outside scope

---

# Validation Rules

Before phase completion:

Required:
- lint passes
- typecheck passes
- imports resolve
- architecture remains intact
- no duplicate systems introduced

---

# Realtime Rules

Warp must:
- support replay
- support reconnect
- support stale recovery
- tolerate duplicate events
- preserve deterministic reconciliation

Realtime must NEVER assume perfect connectivity.

---

# Workflow Rules

Warp must:
- preserve workflow authority
- preserve replayability
- preserve auditability
- preserve deterministic state transitions

No hidden workflow mutation allowed.

---

# AI Rules

Warp must:
- keep AI subordinate to workflows
- preserve approval gates
- preserve auditability
- preserve traceability

AI may never bypass governance.

---

# Frontend Rules

Warp must:
- obey design system
- obey accessibility doctrine
- preserve operational density
- preserve keyboard navigation
- preserve responsive behavior

---

# Backend Rules

Warp must:
- preserve event sourcing principles
- preserve workflow runtime doctrine
- preserve persistence guarantees
- preserve audit logging

---

# Mobile Rules

Warp must:
- preserve operational parity
- preserve realtime behavior
- preserve reconnect handling
- preserve responsive workflows

---

# Forbidden Patterns

Forbidden:
- giant god components
- hidden singleton state
- silent retries
- silent failures
- direct frontend operational ownership
- uncontrolled polling
- hidden websocket state
- duplicate caches
- hidden mutations

---

# Required Patterns

Required:
- deterministic state ownership
- replay-safe logic
- isolated feature domains
- event-driven synchronization
- rollback support
- optimistic reconciliation
- auditability
- observability

---

# Failure Rules

Warp must:
- classify failures
- preserve degraded operation
- preserve recovery capability
- preserve operational visibility

No silent corruption allowed.

---

# Observability Rules

All important systems must expose:
- tracing
- correlation ids
- replayability
- auditability
- failure visibility

---

# Final Doctrine

Warp is an implementation worker.

Doctrine documents define the system.

Architecture stability overrides implementation speed.

Determinism overrides cleverness.

Operational trust overrides convenience.