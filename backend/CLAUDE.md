# Backend Subsystem Guide

## Scope

Backend systems only.

## Includes

- FastAPI
- SQLAlchemy
- Alembic
- Pydantic schemas
- repositories
- auth
- RBAC
- audit logs
- observability
- events
- workflows
- realtime server runtime

## Context Loading

Read only backend files relevant to the task.

Do not load frontend files unless API contract integration requires it.

## Rules

- Preserve deterministic runtime behavior.
- Preserve auditability.
- Preserve event emission for important mutations.
- Preserve repository boundaries.
- Preserve validation gates.
- Do not implement frontend UI.
- Do not implement AI orchestration unless active phase requires it.

## Validation

Backend changes require:
- ruff
- pytest
- import validation