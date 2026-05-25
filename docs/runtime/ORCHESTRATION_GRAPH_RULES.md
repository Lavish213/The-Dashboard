# ORCHESTRATION_GRAPH_RULES

## Purpose

Defines the canonical execution law for orchestration graphs inside the runtime.

This document governs:
- graph structure
- node execution semantics
- dependency resolution
- orchestration scheduling
- graph replay
- graph recovery
- cancellation propagation
- orchestration determinism
- graph ownership boundaries

This is the authoritative orchestration execution doctrine.

---

# Core Doctrine

The orchestration graph is authoritative.

Agents do not control execution flow.

The graph runtime controls:
- scheduling
- dependency resolution
- retries
- recovery
- cancellation
- checkpoints
- execution ordering

Graphs must remain:
- deterministic
- replayable
- auditable
- recoverable
- bounded
- governance-compatible

---

# Graph Definition

A graph is a deterministic execution structure composed of:
- nodes
- edges
- dependencies
- execution policies
- retry policies
- checkpoint rules
- cancellation semantics

Graphs define execution order.

Agents do not define execution order.

---

# Graph Components

Every graph consists of:

```text id="jljf6e"
graph
├── nodes
├── edges
├── execution state
├── dependency rules
├── retry policy
├── checkpoint policy
├── governance policy
├── orchestration metadata
└── replay metadata