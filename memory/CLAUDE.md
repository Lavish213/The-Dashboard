# Memory Subsystem Guide

## Scope

Persistent memory, retrieval, indexing, and context routing.

## Includes

- active context
- decision logs
- retrieval strategy
- embeddings
- vector search
- memory routing
- subsystem context loading

## Rules

- Repo memory is source of truth over chat memory.
- Keep memory files compact.
- Prefer retrieval over full context loading.
- Archive stale memory.
- Do not store unnecessary transient details.
- Do not mix unrelated subsystem memory.

## Validation

Memory changes require:
- context strategy review
- duplicate memory check
- stale information check