# docs/realtime/REALTIME_RUNTIME.md

```md
# Karpathys Platform — Realtime Runtime Canon

Status: LOCKED
Authority Level: TIER 1

---

# Purpose

Realtime is the operational nervous system of Karpathys.

Realtime distributes:
- workflow transitions
- transcript streams
- approvals
- retries
- failures
- reconnect state
- presence
- AI insights

Realtime is NOT:
- best-effort decoration
- optional UX polish
- uncontrolled websocket spam

Realtime is operational infrastructure.

---

# Realtime Doctrine

Realtime is:
- event-driven
- replay-aware
- reconnect-safe
- permission-scoped
- deterministic

The frontend reconstructs operational truth from:
- events
- snapshots
- replay windows

---

# Realtime Architecture

```text
Backend Events
    ↓
Realtime Runtime
    ↓
Subscription Layer
    ↓
WebSocket Transport
    ↓
Frontend Event Reconciliation