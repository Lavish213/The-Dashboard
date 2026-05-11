# Karpathys Platform — Claude Operating Guide

Read this first. Keep responses compact.

## Core Rule

Do not invent architecture. Follow repo docs.

## Doctrine Order

For architecture decisions, read:
1. docs/backend/BACKEND_ARCHITECTURE.md
2. docs/frontend/FRONTEND_ARCHITECTURE.md
3. docs/frontend/DESIGN_SYSTEM.md
4. docs/backend/EVENT_CONTRACTS.md
5. docs/backend/WORKFLOW_RUNTIME.md
6. docs/frontend/STATE_MANAGEMENT.md
7. docs/database/FINAL_SCHEMA.md
8. docs/realtime/REALTIME_RUNTIME.md
9. docs/BUILD_EXECUTION_PLAN.md
10. docs/WARP_EXECUTION_RULES.md

## Active Work

Before coding, read:
- docs/runtime/ACTIVE_CONTEXT.md
- docs/runtime/PHASE_STATUS.md
- docs/runtime/NEXT_ACTIONS.md
- current phase doc

## Output Rules

Be concise.
No giant summaries.
No full file dumps unless requested.
Report only:
- files changed
- validations
- blockers
- next step

## Scope Rules

Only touch files allowed by the active phase.
Never proceed to next phase without approval.
No speculative refactors.
No hidden systems.