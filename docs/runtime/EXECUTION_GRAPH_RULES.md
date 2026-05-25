# EXECUTION_GRAPH_RULES

## Purpose

Defines deterministic execution graph rules for Phase 14 agent orchestration.

This document is canonical runtime law for:
- graph construction
- dependency validation
- execution ordering
- branch behavior
- retry boundaries
- cancellation propagation
- replay guarantees
- failure containment

Execution graphs are deterministic runtime structures.

They are NOT freeform agent conversations.

---

# Core Doctrine

Execution graphs must be:
- deterministic
- acyclic
- replay-safe
- checkpointable
- auditable
- governance-compatible
- bounded by explicit budgets

No graph may execute if its structure is invalid.

---

# Graph Definition

An execution graph is a directed acyclic graph of orchestration nodes.

Each node represents one bounded execution unit.

Allowed node types:
- agent_task
- deterministic_task
- approval_gate
- checkpoint
- router
- join
- retry_boundary
- dead_letter
- cancellation_boundary

Forbidden node types:
- self_mutating_agent
- unbounded_loop
- autonomous_planner_loop
- hidden_side_effect_task
- recursive_agent_spawn

---

# Required Graph Properties

Every graph MUST define:

```text
graph_id
graph_version
root_node_id
node_set
edge_set
execution_budget
retry_policy
governance_policy
created_at