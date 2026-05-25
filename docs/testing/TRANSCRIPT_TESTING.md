# Transcript Testing

## Required Backend Tests

Must test:

- concurrent chunk append
- replay ordering
- websocket event ordering
- pagination correctness
- transcript lifecycle transitions
- recovery after failure
- reconnect sequence recovery
- deterministic replay consistency

---

## Required Frontend Tests

Must test:

- live transcript rendering
- chunk append rendering
- websocket reconnect
- pagination
- transcript status updates
- no duplicate chunk rendering

---

## Validation Gates

Backend:

- pytest
- ruff

Frontend:

- eslint
- typecheck
- production build

---

## Production Failure Conditions

Fail phase if:

- transcripts load entirely into memory
- websocket ordering is nondeterministic
- replay changes transcript state
- duplicate chunks appear
- concurrent writes corrupt ordering
- reconnect duplicates transcript events