# Guardrails

## Repository Rules

- Never scan the full repository unless explicitly required.
- Never load unrelated subsystems by default.
- Never mix frontend, backend, realtime, vision, memory, and Sophia context unless the task requires it.
- Never continue past failed validation without reporting the blocker.
- Never invent architecture outside the doctrine documents.

## Context Rules

- Read docs/runtime/ACTIVE_CONTEXT.md first.
- Read the current phase document second.
- Read the relevant subsystem CLAUDE.md third.
- Load directly relevant files only.
- Use supporting docs only when needed.

## Token Rules

- Keep outputs compact.
- Avoid giant summaries.
- Avoid full file dumps unless requested.
- Avoid repeated explanations.
- Avoid verbose terminal output.
- Prefer changed files, validations, blockers, and next step.

## Execution Rules

- Touch only files allowed by the active phase.
- Do not implement future-phase systems early.
- Do not create duplicate runtimes.
- Do not add dependencies without reason.
- Do not perform speculative refactors.

## Validation Rules

- Run required tests for the touched subsystem.
- Report validation results clearly.
- Report blockers honestly.
- Stop at the phase boundary.