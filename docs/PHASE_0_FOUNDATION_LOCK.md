# Karpathys Platform — Phase 0 Foundation Lock

Status: LOCKED
Phase: 0
Authority: EXECUTION PHASE CANON

---

# Purpose

Phase 0 establishes deterministic project foundations.

This phase exists to:
- stabilize tooling
- stabilize imports
- stabilize runtime environments
- stabilize repository structure
- validate architecture boundaries

NO business logic is allowed during this phase.

NO workflow systems are allowed during this phase.

NO AI systems are allowed during this phase.

This phase is infrastructure only.

---

# Phase Objectives

Required outcomes:
- frontend boots
- backend boots
- imports resolve
- aliases resolve
- lint passes
- typecheck passes
- repo structure validated
- environments validated
- docker validated
- formatting validated

---

# Allowed File Areas

Warp may ONLY modify:

frontend/package.json
frontend/tsconfig.json
frontend/next.config.*
frontend/eslint.*
frontend/prettier.*
frontend/postcss.config.*
frontend/tailwind.config.*
frontend/app/layout.tsx
frontend/providers/*
frontend/styles/*
frontend/config/*

backend/requirements.txt
backend/pyproject.toml
backend/api/main.py
backend/db/session.py
backend/config/*
backend/utils/*

docker-compose.yml
.env.example
README.md

---

# Forbidden Systems

Warp may NOT implement:
- workflows
- transcript systems
- realtime systems
- AI runtime
- approvals
- event runtime
- websocket orchestration
- analytics
- business logic
- repositories
- service logic

Forbidden:
- hidden scaffolding
- speculative architecture
- placeholder workflow engines

---

# Frontend Requirements

Frontend stack:
- Next.js App Router
- TypeScript strict mode
- Tailwind
- Zustand
- TanStack Query
- shadcn/ui
- Framer Motion
- React Hook Form
- Zod

Frontend must support:
- path aliases
- strict typing
- deterministic imports
- responsive root layout

---

# Backend Requirements

Backend stack:
- FastAPI
- SQLAlchemy 2.x
- Alembic
- Pydantic v2
- asyncpg
- Redis-ready architecture
- structured logging

Backend must support:
- async runtime
- deterministic imports
- clean dependency boundaries
- startup validation

---

# Tooling Requirements

Required:
- ESLint
- Prettier
- strict TypeScript
- Ruff
- Black
- import sorting
- deterministic formatting

---

# Docker Requirements

Docker must:
- boot frontend
- boot backend
- support local development
- support Railway deployment compatibility

No production optimizations yet.

---

# Environment Requirements

Environment handling must support:
- local development
- Railway
- mobile compatibility
- future staging environments

No secrets committed.

---

# Import Doctrine

Required:
- deterministic aliases
- no circular imports
- no relative import chaos

Frontend aliases:

@
@/components
@/features
@/lib
@/stores

Backend imports must remain layered.

---

# Accessibility Foundation

Required:
- semantic HTML root
- reduced motion support foundation
- dark mode foundation
- keyboard-safe layouts

---

# Responsive Foundation

Required breakpoints:

mobile
tablet
desktop
ultrawide

Responsive shell must exist.

---

# Validation Requirements

Before phase completion:

Required:
- npm install succeeds
- pip install succeeds
- frontend boots
- backend boots
- no type errors
- no lint errors
- no import failures
- no duplicate configs
- no dependency conflicts

---

# Output Requirements

Warp must output:
- modified files
- validation results
- unresolved blockers
- dependency additions
- architecture concerns

Warp must NOT silently modify unrelated files.

---

# Completion Gate

Phase 0 completes ONLY if:
- repo stable
- tooling stable
- imports stable
- runtime stable
- architecture untouched
- no speculative systems added

---

# Final Doctrine

Phase 0 exists to eliminate foundational instability before implementation begins.

Stability first.

Determinism first.

Architecture preservation first.