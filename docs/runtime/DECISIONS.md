# Decisions

## 2026-05-11 — Use Phase-Gated Execution

Decision:
Karpathys will be built phase by phase with strict boundaries.

Reason:
Prevents architecture drift, duplicate systems, and token-heavy rework.

## 2026-05-11 — Use Repo Memory Instead Of Chat Memory

Decision:
Durable project state lives in markdown files inside the repository.

Reason:
Reduces repeated prompting and prevents long chat context from becoming the source of truth.

## 2026-05-11 — Use Scoped Context Loading

Decision:
Agents must load only active context, subsystem instructions, and directly relevant files.

Reason:
Improves output quality and reduces token waste.

## 2026-05-11 — Keep Root CLAUDE.md Lean

Decision:
Root CLAUDE.md acts as a routing guide only.

Reason:
Large root instruction files are loaded too often and become token-heavy.

## 2026-05-11 — Separate Planning From Execution

Decision:
Planning and implementation should happen in separate scoped sessions when tasks are large.

Reason:
Keeps execution context clean and avoids wasted rebuilds.