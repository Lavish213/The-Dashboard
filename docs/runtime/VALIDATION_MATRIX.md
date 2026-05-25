# Validation Matrix

## Backend Changes

Required:
- pytest
- ruff
- import verification if dependencies changed

---

## Frontend Changes

Required:
- typecheck
- lint
- build verification

---

## Websocket / Realtime Changes

Required:
- reconnect verification
- duplicate event verification
- sequence verification
- Playwright websocket audit

---

## Runtime Infrastructure Changes

Required:
- deterministic state verification
- replay protection verification
- runtime event verification

---

## Transcript Runtime Changes

Required:
- stream continuity verification
- chunk ordering verification
- reconnect stream verification

---

## Governance Runtime Changes

Required:
- approval flow verification
- escalation verification
- audit trail verification

---

## AI Runtime Changes

Required:
- retrieval verification
- memory verification
- hallucination safeguards
- deterministic fallback verification

---

## Phase Completion Rule

A phase is complete only when:
- validations pass
- boundaries remain intact
- forbidden scope was not crossed
- runtime stability verified