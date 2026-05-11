# Command Registry

## Purpose

Reusable low-token command patterns for Karpathys execution.

## Phase Closeout

Use when finishing a phase.

Required output:
- files changed
- validations passed
- blockers
- forbidden systems check
- next phase

## Backend Validate

Commands:
- backend pytest
- backend ruff
- backend import validation

Output:
- pass/fail only
- failing test names only
- blocker summary only

## Frontend Validate

Commands:
- frontend typecheck
- frontend lint
- frontend build

Output:
- pass/fail only
- route/build failures only
- blocker summary only

## Architecture Audit

Checks:
- no duplicate runtimes
- no future-phase leakage
- no unrelated subsystem edits
- no speculative abstractions

Output:
- clean or list violations

## Git Check

Commands:
- git status
- git diff --stat
- git log --oneline -5

Output:
- concise summary only