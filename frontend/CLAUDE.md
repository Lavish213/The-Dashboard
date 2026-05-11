# Frontend Subsystem Guide

## Scope

Frontend systems only.

## Includes

- Next.js App Router
- React components
- Zustand stores
- TanStack Query
- UI primitives
- layouts
- navigation
- frontend realtime client
- workflow views
- transcript views
- approval views

## Context Loading

Read only frontend files relevant to the task.

Do not load backend internals unless API contracts require it.

## Rules

- Preserve design system.
- Preserve accessibility.
- Preserve responsive behavior.
- Preserve operational density.
- Do not own backend truth.
- Do not invent workflow states.
- Do not bypass realtime/event contracts.

## Validation

Frontend changes require:
- typecheck
- lint
- build when route/layout/components are touched