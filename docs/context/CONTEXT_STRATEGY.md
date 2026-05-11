# Context Strategy

## Purpose

This document defines how Karpathys controls AI context usage.

The goal is high reasoning quality with minimal irrelevant context.

## Core Principle

Use retrieval-first execution.

Do not stuff the context window with unrelated architecture, old logs, or full repository scans.

## Loading Order

1. docs/runtime/ACTIVE_CONTEXT.md
2. current phase document
3. relevant subsystem CLAUDE.md
4. directly relevant files
5. supporting doctrine docs only if needed

## Subsystem Boundaries

Backend tasks should avoid frontend context unless API/UI integration is required.

Frontend tasks should avoid backend internals unless contract integration is required.

Realtime tasks should load realtime protocol, event contracts, and websocket files only.

Workflow tasks should load workflow runtime docs, event contracts, and workflow files only.

Transcript tasks should not load AI runtime unless transcript intelligence is being implemented.

AI tasks should not mutate authoritative workflow state unless explicitly approved by governance rules.

## Session Strategy

Use fresh sessions for unrelated tasks.

Use compact only when continuing the same task.

Use clear when switching tasks.

Separate planning sessions from execution sessions for large work.

## Output Strategy

Default output:
- files changed
- validations
- blockers
- next step

Avoid:
- full file dumps
- long summaries
- repeated architecture explanations
- unrelated recommendations

## Long-Term Goal

Karpathys should operate with scoped retrieval, durable repo memory, and phase-gated execution instead of giant prompts.