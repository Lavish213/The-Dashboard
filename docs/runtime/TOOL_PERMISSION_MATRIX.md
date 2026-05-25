# TOOL_PERMISSION_MATRIX

## Purpose

Defines the canonical tool permission model for all runtime systems.

This document governs:
- tool access boundaries
- agent tool permissions
- orchestration tool routing
- governance approval rules
- human approval rules
- external side-effect controls
- tool audit requirements
- tool budget enforcement
- tool failure handling
- replay compatibility
- production safety

Tool execution is privileged runtime behavior.

No tool may execute without explicit permission.

---

# Core Doctrine

Tool access is deny-by-default.

All tool execution must be:
- permission-checked
- governance-compatible
- auditable
- budgeted
- bounded
- replay-visible
- failure-isolated

Agents do not own tool permissions.

Orchestration grants scoped tool access.

Governance may override or deny tool access.

---

# Runtime Philosophy

Tools are external capability surfaces.

Tools may:
- mutate state
- access sensitive systems
- create irreversible side effects
- consume tokens
- consume money
- affect users
- affect external systems

Because of this, tool execution must remain strictly controlled.

---

# Permission Authority Order

Tool permission authority order:

```text
human_operator
governance_runtime
orchestration_runtime
agent_runtime
tool_adapter