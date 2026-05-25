# CONTEXT_ASSEMBLY_RULES

## Purpose

Defines the canonical context assembly architecture for all runtime systems.

This document governs:
- context retrieval
- context construction
- context prioritization
- context truncation
- context governance
- context safety
- token budgeting
- memory layering
- runtime context injection
- agent context boundaries
- replay-compatible context behavior
- deterministic prompt assembly

Context assembly is controlled runtime infrastructure.

It is not unrestricted memory concatenation.

---

# Core Doctrine

All context must be:
- scoped
- bounded
- relevant
- attributable
- auditable
- governance-compatible
- token-budgeted
- replay-compatible

Uncontrolled context injection is forbidden.

---

# Runtime Philosophy

Context is execution fuel.

Bad context causes:
- hallucinations
- governance violations
- prompt drift
- token exhaustion
- replay divergence
- unsafe autonomy
- orchestration instability

Context systems must prioritize:
- correctness over volume
- relevance over recall
- determinism over convenience

---

# Canonical Context Definition

Context is the structured runtime information injected into execution scope.

Context may include:
- system instructions
- workflow state
- orchestration metadata
- memory records
- retrieval results
- summaries
- governance directives
- runtime policies
- active session state

Context is never arbitrary.

---

# Context Ownership

Every context block MUST define:
- owner
- source
- scope
- timestamp
- provenance
- token size
- trust level

Anonymous context is forbidden.

---

# Canonical Context Layers

Canonical runtime context layers:

```text id="f8u2oz"
system_context
runtime_context
governance_context
workflow_context
graph_context
session_context
memory_context
retrieval_context
tool_context
user_context
ephemeral_context