# Sophia Subsystem Guide

## Scope

Sophia voice and AI agent systems only.

## Includes

- voice runtime
- phone agent behavior
- conversation state
- escalation logic
- compliance behavior
- post-call intelligence
- AI provider routing

## Rules

- Sophia is not the platform authority.
- Sophia cannot bypass approvals.
- Sophia cannot mutate critical operational state without governance.
- Sophia outputs must be traceable.
- Realtime voice behavior must remain deterministic where possible.

## Do Not Load Unless Required

- frontend design system
- unrelated backend CRUD
- vision systems
- mobile UI

## Validation

Sophia changes require:
- voice runtime tests
- provider import validation
- compliance rule validation