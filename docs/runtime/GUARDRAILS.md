# Runtime Guardrails

## Core Doctrine

- Deterministic systems first.
- Autonomous systems second.
- Human control above all runtime layers.
- Runtime state must remain inspectable.
- Every major action should be traceable.

---

## Forbidden Patterns

Do not:
- collapse phases together
- add AI early
- bypass validation
- create hidden runtime state
- allow uncontrolled agent execution
- build giant conversational workflows
- depend on massive session memory

---

## Runtime Requirements

- Runtime events must be deterministic.
- Event ordering must be stable.
- Reconnect behavior must be safe.
- Duplicate event prevention required.
- Runtime state transitions must be auditable.

---

## Context Discipline

- Keep sessions focused.
- Use canonical docs.
- Prefer structured state.
- Minimize unnecessary context growth.
- Preserve important decisions externally.

---

## Validation Discipline

Never mark a phase complete without:
- required validations
- runtime verification
- boundary verification
- reconnect verification if realtime touched