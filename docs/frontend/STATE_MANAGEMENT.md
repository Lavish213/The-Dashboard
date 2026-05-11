# Karpathys Platform — State Management Canon

Status: LOCKED
Authority Level: TIER 1
Inherits From:
- FRONTEND_ARCHITECTURE.md
- EVENT_CONTRACTS.md
- WORKFLOW_RUNTIME.md

Last Updated: 2026-05

---

# Purpose

This document defines the authoritative frontend state architecture for Karpathys.

The frontend is:
- realtime-native
- workflow-driven
- event-synchronized
- operationally deterministic

State systems must prioritize:
- consistency
- recoverability
- replay safety
- UI responsiveness
- operational trust

The frontend NEVER owns operational truth.

The backend remains authoritative.

---

# Core Philosophy

Frontend state exists to:
- render backend truth
- provide responsive UX
- manage transient UI interactions
- coordinate realtime updates
- support optimistic interactions safely

Frontend state does NOT:
- replace backend state
- invent workflow truth
- persist operational authority
- bypass event systems

---

# State Hierarchy

```text
Backend Authoritative State
    ↓
Realtime Event Stream
    ↓
Server Cache Layer
    ↓
Feature State
    ↓
Ephemeral UI State