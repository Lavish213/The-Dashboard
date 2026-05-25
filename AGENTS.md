# AGENTS

## Purpose

Repository-wide operational rules for all agent runtimes inside Karpathys Platform.

This file is the lightweight root coordination layer.

Canonical runtime behavior lives in:
- docs/runtime/AGENT_CONTRACTS.md
- docs/runtime/TOKEN_BUDGETS.md
- docs/runtime/GOVERNANCE_RULES.md
- docs/runtime/ACTIVE_CONTEXT.md
- docs/runtime/PHASE_STATUS.md

---

# Runtime Doctrine

The system is:
- deterministic first
- governance enforced
- replayable
- checkpointable
- audit-driven
- human controlled

Agents are workers.

The orchestration runtime is authoritative.

---

# Agent Categories

Current runtime supports:
- orchestration agents
- research agents
- Sophia runtime agents
- governance agents
- retrieval agents
- execution agents
- monitoring agents

All agent behavior must comply with:
```text id="xbs0pv"
docs/runtime/AGENT_CONTRACTS.md