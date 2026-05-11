# Low Token Execution Protocol

## Purpose

Reduce token waste while preserving engineering quality.

## Default Output Format

Use this format unless asked otherwise:

Files changed:
- ...

Validations:
- ...

Blockers:
- ...

Next step:
- ...

## Prompt Rules

- Keep prompts task-specific.
- Batch related instructions into one message.
- Avoid follow-up correction chains when possible.
- Use fresh sessions for unrelated tasks.
- Use current repo memory instead of restating architecture.

## Execution Rules

- Read active context first.
- Read only relevant subsystem docs.
- Avoid full repository scans.
- Avoid dumping large command outputs.
- Summarize logs compactly.
- Preserve validation gates.

## Terminal Rules

Prefer compact commands.

Good:
- pytest tests/test_workflows.py -q
- ruff check workflows tests/test_workflows.py
- npm run typecheck

Avoid:
- printing full logs unless debugging requires it
- recursive tree dumps
- full git diff dumps without scope

## Model Strategy

Use deeper reasoning for:
- architecture
- debugging hard failures
- phase planning

Use execution mode for:
- implementation
- validation
- file edits
- small fixes

## Stop Conditions

Stop immediately when:
- validation fails
- architecture conflict appears
- missing dependency is discovered
- phase boundary would be crossed