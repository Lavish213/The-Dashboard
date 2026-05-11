# Karpathys Platform — Event Contracts Canon

Status: LOCKED
Authority Level: TIER 0
Last Updated: 2026-05
Overrides: All event/realtime documents

---

# Purpose

The Karpathys event system is the canonical nervous system of the platform.

Events are the authoritative operational timeline.

Every important action:
- emits an event
- persists an event
- references an event
- replays from events

Events are NOT:
- analytics only
- websocket payloads only
- debugging helpers

Events ARE:
- operational truth
- workflow history
- replay infrastructure
- audit infrastructure
- realtime coordination infrastructure

---

# Golden Doctrine

## Every Important Action Is An Event

Required:
- workflow transitions
- approvals
- escalations
- retries
- AI decisions
- transcript lifecycle changes
- lead lifecycle changes
- realtime presence changes
- integrations
- failures
- recovery actions

Forbidden:
- hidden mutations
- silent state changes
- invisible retries
- invisible AI actions

---

# Event Hierarchy

```text
Domain Events
    ↓
Workflow Events
    ↓
Realtime Events
    ↓
UI Reactions