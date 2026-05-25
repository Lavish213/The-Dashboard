"""
Research Runtime contracts — immutable input/output types for Phase 13.

All dataclasses are frozen. No mutable state crosses research runtime boundaries.
No embeddings, no semantic retrieval, no autonomous behavior.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from models.enums import (
    ResearchEvidenceStatus,
    ResearchJobStatus,
    ResearchMemoryScope,
    ResearchPlanStatus,
    ResearchTaskStatus,
)

# ---------------------------------------------------------------------------
# Job contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchJobSpec:
    """Input for creating a new research job."""

    job_key: str
    token_budget: int = 16384
    max_depth: int = 10
    sophia_session_id: UUID | None = None
    workflow_id: UUID | None = None
    initiated_by: UUID | None = None
    plan_id: UUID | None = None
    job_metadata: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchJobRecord:
    """Immutable snapshot of a research job state."""

    job_id: UUID
    job_key: str
    status: ResearchJobStatus
    token_budget: int
    tokens_used: int
    task_count: int
    completed_task_count: int
    max_depth: int
    current_depth: int
    checkpoint_state: dict | None
    job_metadata: dict
    created_at: datetime
    sophia_session_id: UUID | None = None
    workflow_id: UUID | None = None
    initiated_by: UUID | None = None
    plan_id: UUID | None = None
    cancel_reason: str | None = None
    error: str | None = None
    started_at: datetime | None = None
    paused_at: datetime | None = None
    completed_at: datetime | None = None
    cancelled_at: datetime | None = None


# ---------------------------------------------------------------------------
# Task contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchTaskSpec:
    """Input for creating a research task."""

    job_id: UUID
    task_index: int
    task_type: str
    input_payload: dict
    depth: int = 0
    max_retries: int = 3
    task_key: str | None = None


@dataclass(frozen=True)
class ResearchTaskRecord:
    """Immutable snapshot of a research task state."""

    task_id: UUID
    job_id: UUID
    task_index: int
    task_type: str
    status: ResearchTaskStatus
    input_payload: dict
    depth: int
    retry_count: int
    max_retries: int
    tokens_input: int
    tokens_output: int
    created_at: datetime
    task_key: str | None = None
    output_payload: dict | None = None
    error: str | None = None
    governance_verdict: dict | None = None
    approval_id: UUID | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class ResearchTaskDependencySpec:
    """Edge in the research task DAG."""

    job_id: UUID
    upstream_task_id: UUID
    downstream_task_id: UUID


# ---------------------------------------------------------------------------
# Task graph contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchGraphSpec:
    """Full DAG specification: tasks + dependency edges."""

    job_id: UUID
    tasks: tuple[ResearchTaskSpec, ...]
    dependencies: tuple[ResearchTaskDependencySpec, ...]


@dataclass(frozen=True)
class ResearchGraphOrder:
    """Result of topological sort — deterministic execution order."""

    job_id: UUID
    task_indices: tuple[int, ...]   # 0-based, topologically sorted
    levels: tuple[tuple[int, ...], ...]  # groups that can run in parallel


# ---------------------------------------------------------------------------
# Evidence contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchEvidenceSpec:
    """Input for recording a piece of evidence."""

    job_id: UUID
    source_uri: str
    source_type: str
    content_hash: str
    provenance: dict
    snapshot: dict
    task_id: UUID | None = None
    content_snippet: str | None = None
    score: float = 0.0
    citation_ref: str | None = None


@dataclass(frozen=True)
class ResearchEvidenceRecord:
    """Immutable evidence snapshot."""

    evidence_id: UUID
    job_id: UUID
    status: ResearchEvidenceStatus
    source_uri: str
    source_type: str
    content_hash: str
    score: float
    provenance: dict
    snapshot: dict
    created_at: datetime
    task_id: UUID | None = None
    content_snippet: str | None = None
    citation_ref: str | None = None


# ---------------------------------------------------------------------------
# Memory contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchMemorySpec:
    """Input for writing a memory entry."""

    job_id: UUID
    scope: ResearchMemoryScope
    memory_key: str
    value: dict
    ttl_seconds: int | None = None   # None = no expiry
    task_id: UUID | None = None


@dataclass(frozen=True)
class ResearchMemoryEntry:
    """Immutable memory read result."""

    memory_id: UUID
    job_id: UUID
    scope: ResearchMemoryScope
    memory_key: str
    value: dict
    created_at: datetime
    task_id: UUID | None = None
    expires_at: datetime | None = None


# ---------------------------------------------------------------------------
# Plan contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchPlanSpec:
    """Input for creating a research plan."""

    plan_key: str
    goal: str
    steps: tuple[dict, ...]
    constraints: dict = field(default_factory=dict)
    job_id: UUID | None = None


@dataclass(frozen=True)
class ResearchPlanRecord:
    """Immutable snapshot of a research plan."""

    plan_id: UUID
    plan_key: str
    goal: str
    status: ResearchPlanStatus
    revision: int
    steps: list
    constraints: dict
    created_at: datetime
    job_id: UUID | None = None
    checkpoint_state: dict | None = None
    approval_id: UUID | None = None


@dataclass(frozen=True)
class ResearchPlanRevision:
    """Input for revising an existing plan."""

    plan_id: UUID
    goal: str | None
    steps: tuple[dict, ...] | None
    constraints: dict | None
    actor_id: UUID | None = None


# ---------------------------------------------------------------------------
# Checkpoint
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchCheckpoint:
    """Point-in-time checkpoint for resumable replay."""

    checkpoint_id: str
    job_id: UUID
    task_index: int
    token_budget_remaining: int
    state_blob: dict
    captured_at: datetime


# ---------------------------------------------------------------------------
# Safety contracts
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchSafetyConfig:
    """Safety ceiling configuration for a research job."""

    max_tokens: int
    max_depth: int
    max_tasks: int
    token_warning_threshold: float = 0.8   # warn at 80% consumed
    timeout_seconds: int | None = None


@dataclass(frozen=True)
class ResearchBudgetState:
    """Current budget consumption snapshot."""

    job_id: UUID
    tokens_used: int
    token_budget: int
    tokens_remaining: int
    budget_fraction: float   # tokens_used / token_budget
    over_budget: bool
    near_limit: bool
    task_count: int
    current_depth: int


# ---------------------------------------------------------------------------
# Governance
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchGovernanceCheck:
    """Input for a governance check on a research task action."""

    job_id: UUID
    task_id: UUID
    action: str          # e.g. "research.task.execute"
    risk_tier: str
    actor_id: UUID | None = None
    context: dict = field(default_factory=dict)


@dataclass(frozen=True)
class ResearchGovernanceResult:
    """Result of a research governance check."""

    action: str
    permitted: bool
    requires_approval: bool
    approval_id: UUID | None
    classification: str
    reason: str | None = None


# ---------------------------------------------------------------------------
# Replay
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchReplayFrame:
    """One frame in a deterministic research job replay."""

    frame_index: int
    event_type: str
    job_id: UUID
    task_id: UUID | None
    payload: dict
    emitted_at: datetime


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResearchMetrics:
    """Aggregated research runtime metrics over a time period."""

    total_jobs: int
    jobs_completed: int
    jobs_cancelled: int
    jobs_failed: int
    total_tasks: int
    tasks_completed: int
    tasks_failed: int
    tasks_retried: int
    total_evidence: int
    evidence_accepted: int
    evidence_rejected: int
    evidence_deduplicated: int
    governance_checks: int
    budget_warnings: int
    depth_limit_hits: int
    period_start: datetime
    period_end: datetime
