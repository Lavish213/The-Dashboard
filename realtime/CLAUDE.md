# Realtime Subsystem Guide

## Scope

Realtime synchronization systems only.

## Includes

- websocket protocol
- connection lifecycle
- subscriptions
- replay
- reconnect
- event deduplication
- stale state handling
- realtime health

## Rules

- Events are authoritative synchronization signals.
- Reconnect must restore subscriptions.
- Duplicate events must be tolerated.
- Global ordering is not guaranteed.
- Aggregate ordering matters.
- Permission boundaries must be respected.

## Do Not Load Unless Required

- transcript intelligence
- AI orchestration
- unrelated frontend styling
- unrelated backend services

## Validation

Realtime changes require:
- backend realtime tests
- frontend typecheck if frontend client touched
- build if realtime page/provider touched