# Low Token Execution Protocol

## Purpose

Reduce token waste while preserving engineering quality.

---

## Default Output Format

Use this format unless explicitly asked otherwise.

Files changed:
- ...

Validations:
- ...

Blockers:
- ...

Next step:
- ...

---

## Prompt Rules

- Keep prompts task-specific.
- Batch related instructions into one message.
- Avoid correction chains when possible.
- Use fresh sessions for unrelated tasks.
- Reuse canonical runtime docs instead of repeating architecture.
- Do not restate completed phases unnecessarily.

---

## Execution Rules

- Read ACTIVE_CONTEXT.md first.
- Read only relevant subsystem docs.
- Avoid broad repository scans.
- Avoid unnecessary tool calls.
- Avoid giant summaries.
- Preserve deterministic phase boundaries.
- Stop when current scope is complete.

---

## Terminal Rules

Prefer compact commands.

Good:
- pytest tests/test_runtime.py -q
- ruff check backend tests
- npm run typecheck

Avoid:
- recursive tree dumps
- giant git diffs
- printing full logs unnecessarily
- repeated repo-wide scans

---

## Runtime Rules

Use deeper reasoning for:
- architecture
- runtime debugging
- phase planning
- deterministic systems

Use execution mode for:
- implementation
- validation
- targeted edits
- small fixes

---

## Stop Conditions

Stop immediately when:
- validation fails
- architecture conflict appears
- missing dependency discovered
- phase boundary would be crossed
- unrelated subsystem exploration begins

---

## Session Discipline

- Prefer short focused sessions.
- Reset sessions before heavy context rot.
- Preserve decisions in canonical docs.
- Use structured handoffs between sessions.
- Never rely on giant conversational memory.