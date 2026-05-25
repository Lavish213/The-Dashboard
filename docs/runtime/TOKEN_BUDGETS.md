# TOKEN_BUDGETS

## Purpose

Defines token budgeting rules for Phase 14 agent orchestration and all future AI-controlled execution layers.

This document is canonical runtime law for:
- token ceilings
- execution budgets
- context budgets
- retry budgets
- graph-level budget enforcement
- agent-level budget enforcement
- budget exhaustion behavior
- cost visibility
- context discipline

Token budgets are runtime constraints.

They are NOT suggestions.

---

# Core Doctrine

All AI execution must be bounded.

No agent, graph, workflow, research job, Sophia session, or orchestration runtime may execute without explicit budgets.

Budgets must be:
- declared before execution
- enforced during execution
- audited after execution
- replay-safe
- tied to runtime events

Silent budget overflow is forbidden.

---

# Budget Scope Levels

Budgets exist at five levels:

1. platform budget
2. phase budget
3. graph budget
4. agent budget
5. call budget

Lower-level budgets may not exceed higher-level budgets.

---

# Platform Budget

Platform budget controls global usage across the runtime.

Tracks:
- total input tokens
- total output tokens
- total cached tokens
- total tool calls
- total model calls
- total execution cost estimate

Platform budget is used for:
- global rate limiting
- abuse prevention
- cost controls
- operational visibility

---

# Phase Budget

Phase budget controls work inside a runtime phase.

Examples:
- Phase 14 orchestration execution
- Phase 12 Sophia session runtime
- Phase 13 research runtime

Phase budget must define:
- max total tokens
- max total model calls
- max total retries
- max total execution depth
- max total runtime duration

---

# Graph Budget

Every orchestration graph MUST define:

```text
max_graph_tokens
max_graph_input_tokens
max_graph_output_tokens
max_graph_model_calls
max_graph_tool_calls
max_graph_retries
max_graph_depth
max_graph_nodes
max_graph_runtime_seconds