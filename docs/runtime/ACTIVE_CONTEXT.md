# Active Context

Current Project:
- Karpathys Platform

Current Phase:
- Phase 15 — Context + Memory Runtime

Current Objective:
- Implement deterministic context + memory runtime for bounded, replay-safe,
  governance-compatible context assembly.
- Add enforcement, ranking, sanitization, memory, and replay layers on top
  of existing Phase 10 context infrastructure.
- No rewrite of Phase 10. No duplicate systems.

Completed:
- Phase 0 Foundation Lock
- Phase 1 Design System
- Phase 2 App Shell + Routing
- Phase 3 Backend Core Runtime
- Phase 4 Realtime Runtime Foundation
- Phase 5 Workflow Runtime
- Phase 6 Transcript System Foundation
- Phase 7 Deterministic Realtime Runtime
- Phase 8 AI Runtime Foundation
- Phase 9 Transcript Runtime + Streaming
- Phase 10 Context Infrastructure Layer
- Phase 11 Governance + Approval Runtime
- Phase 12 Sophia Runtime
- Phase 13 Karoathys Research Runtime
- Phase 14 Agent Orchestration + Governance Enforcement Integration

Phase 15 deliverables (in progress):
- models/enums.py — ContextBudgetLevel (5 levels: platform, phase, graph, agent, call)
- context/exceptions.py — ContextError hierarchy
- context/budget.py — ContextBudgetEnforcer (stateless, 5-level enforcement)
- context/ranking.py — ContextItemRanker (deterministic: priority, recency, score)
- context/sanitizer.py — ContextItemSanitizer (secret detection, fail-closed)
- context/memory.py — ContextMemoryRuntime (scoped, bounded, no global state)
- context/replay.py — ContextReplayRuntime (fail-closed, expired/archived blocked)
- context/runtime.py — ContextRuntime (session-scoped lazy-init coordinator)
- tests/test_context_runtime.py — Phase 15 integration tests

Do Not Implement Yet:
- real LLM calls
- autonomous agent loops
- embeddings / vector search
- LangGraph orchestration
- external APIs
- frontend UI for context

Current Output Mode:
- Compact
- Files changed only
- Validation results only
- Blockers only
- Minimal explanations

Validation Required:
- backend pytest
- backend ruff
