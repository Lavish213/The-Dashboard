
"""schema_reconcile

Revision ID: 3ae52ccaf032
Revises: 0002
Create Date: 2026-05-18 07:17:45.077108
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "3ae52ccaf032"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    transcript_source_type = postgresql.ENUM(
        "call",
        "upload",
        "realtime",
        "manual",
        name="transcriptsourcetype",
        create_type=False,
    )
    transcript_source_type.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "approval_delegations",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("delegation_key", sa.String(length=512), nullable=False),
        sa.Column("delegator_id", sa.UUID(), nullable=False),
        sa.Column("delegate_id", sa.UUID(), nullable=False),
        sa.Column("approval_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("risk_tiers", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", sa.Enum("active", "revoked", "expired", name="delegationstatus", create_type=False), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoke_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("delegation_key"),
    )
    op.create_index("ix_approval_delegations_delegate_id", "approval_delegations", ["delegate_id"])
    op.create_index("ix_approval_delegations_delegator_id", "approval_delegations", ["delegator_id"])
    op.create_index("ix_approval_delegations_status", "approval_delegations", ["status"])

    op.create_table(
        "context_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("assembly_key", sa.String(length=512), nullable=False),
        sa.Column("status", sa.Enum("active", "archived", "expired", name="contextsnapshotstatus"), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=True),
        sa.Column("transcript_id", sa.UUID(), nullable=True),
        sa.Column("execution_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("layer_types", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("window_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("assembly_params", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("assembly_key"),
    )
    op.create_index("ix_context_snapshots_created_at", "context_snapshots", ["created_at"])
    op.create_index("ix_context_snapshots_status", "context_snapshots", ["status"])
    op.create_index("ix_context_snapshots_workflow_id", "context_snapshots", ["workflow_id"])

    op.create_table(
        "domain_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("event_id", sa.String(), nullable=False),
        sa.Column("channel", sa.String(), nullable=False),
        sa.Column("seq_num", sa.BigInteger(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("correlation_id", sa.String(), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("channel", "seq_num", name="uq_domain_events_channel_seq_num"),
        sa.UniqueConstraint("event_id", name="uq_domain_events_event_id"),
    )
    op.create_index("ix_domain_events_channel_seq_num", "domain_events", ["channel", "seq_num"])
    op.create_index("ix_domain_events_event_type", "domain_events", ["event_type"])

    op.create_table(
        "governance_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "policy_evaluated",
                "approval_routed",
                "escalation_triggered",
                "escalation_resolved",
                "quorum_vote_cast",
                "quorum_met",
                "override_applied",
                "freeze_activated",
                "freeze_deactivated",
                "kill_switch_triggered",
                "policy_superseded",
                "policy_snapshot_captured",
                "delegation_granted",
                "delegation_revoked",
                "action_denied",
                "freeze_propagated",
                "invariant_violated",
                name="governanceeventtype",
            ),
            nullable=False,
        ),
        sa.Column("policy_id", sa.UUID(), nullable=True),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("correlation_id", sa.UUID(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_governance_events_approval_id", "governance_events", ["approval_id"])
    op.create_index("ix_governance_events_correlation_id", "governance_events", ["correlation_id"])
    op.create_index("ix_governance_events_created_at", "governance_events", ["created_at"])
    op.create_index("ix_governance_events_event_type", "governance_events", ["event_type"])
    op.create_index("ix_governance_events_policy_id", "governance_events", ["policy_id"])

    op.create_table(
        "governance_policies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("policy_key", sa.String(length=256), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("active", "inactive", "superseded", "archived", name="governancepolicystatus"), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("action_patterns", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("classification", sa.Enum("safe", "restricted", "privileged", "forbidden", name="actionclassification"), nullable=False),
        sa.Column("risk_tier", sa.Enum("standard", "elevated", "high", "critical", name="risktier"), nullable=False),
        sa.Column("routing_strategy", sa.Enum("direct", "escalation_chain", "quorum", "any_of", name="approvalroutingstrategy"), nullable=False),
        sa.Column("approver_ids", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("escalation_chain", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("quorum_required", sa.Integer(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("escalation_timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("inherited_from", sa.String(length=256), nullable=True),
        sa.Column("rules", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_by", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("policy_key", "version", name="uq_governance_policies_key_version"),
    )
    op.create_index("ix_governance_policies_policy_key", "governance_policies", ["policy_key"])
    op.create_index("ix_governance_policies_risk_tier", "governance_policies", ["risk_tier"])
    op.create_index("ix_governance_policies_status", "governance_policies", ["status"])

    op.create_table(
        "research_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "job_created",
                "job_started",
                "job_paused",
                "job_resumed",
                "job_completed",
                "job_failed",
                "job_cancelled",
                "job_checkpointed",
                "task_created",
                "task_started",
                "task_completed",
                "task_failed",
                "task_cancelled",
                "task_skipped",
                "task_retried",
                "evidence_recorded",
                "evidence_accepted",
                "evidence_rejected",
                "evidence_deduplicated",
                "memory_written",
                "memory_expired",
                "memory_cleared",
                "plan_created",
                "plan_revised",
                "plan_completed",
                "plan_abandoned",
                "governance_checked",
                "budget_warning",
                "budget_exceeded",
                "depth_limit_reached",
                "timeout_triggered",
                "dead_letter",
                "replay_started",
                "replay_completed",
                name="researcheventtype",
            ),
            nullable=False,
        ),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("correlation_id", sa.String(length=256), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("emitted_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_events_emitted_at", "research_events", ["emitted_at"])
    op.create_index("ix_research_events_event_type", "research_events", ["event_type"])
    op.create_index("ix_research_events_job_id", "research_events", ["job_id"])

    op.create_table(
        "research_plans",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("plan_key", sa.String(length=512), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Enum("draft", "active", "revised", "completed", "abandoned", name="researchplanstatus"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("goal", sa.Text(), nullable=False),
        sa.Column("steps", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("constraints", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checkpoint_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("plan_key"),
    )
    op.create_index("ix_research_plans_job_id", "research_plans", ["job_id"])
    op.create_index("ix_research_plans_status", "research_plans", ["status"])

    op.create_table(
        "sophia_events",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "session_started",
                "session_completed",
                "session_cancelled",
                "session_failed",
                "turn_started",
                "turn_completed",
                "turn_interrupted",
                "turn_cancelled",
                "tool_permitted",
                "tool_blocked",
                "governance_evaluated",
                "handoff_requested",
                "handoff_accepted",
                "handoff_completed",
                "checkpoint_saved",
                "context_assembled",
                "cancellation_requested",
                "recovery_initiated",
                name="sophiaeventtype",
            ),
            nullable=False,
        ),
        sa.Column("session_id", sa.UUID(), nullable=True),
        sa.Column("turn_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("correlation_id", sa.String(length=256), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("emitted_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sophia_events_event_type", "sophia_events", ["event_type"])
    op.create_index("ix_sophia_events_session_id", "sophia_events", ["session_id"])
    op.create_index("ix_sophia_events_turn_id", "sophia_events", ["turn_id"])

    op.create_table(
        "research_jobs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_key", sa.String(length=512), nullable=False),
        sa.Column("status", sa.Enum("queued", "running", "paused", "completed", "failed", "cancelled", name="researchjobstatus"), nullable=False),
        sa.Column("sophia_session_id", sa.UUID(), nullable=True),
        sa.Column("workflow_id", sa.UUID(), nullable=True),
        sa.Column("initiated_by", sa.UUID(), nullable=True),
        sa.Column("plan_id", sa.UUID(), nullable=True),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("task_count", sa.Integer(), nullable=False),
        sa.Column("completed_task_count", sa.Integer(), nullable=False),
        sa.Column("max_depth", sa.Integer(), nullable=False),
        sa.Column("current_depth", sa.Integer(), nullable=False),
        sa.Column("checkpoint_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("job_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_key"),
    )
    op.create_index("ix_research_jobs_sophia_session_id", "research_jobs", ["sophia_session_id"])
    op.create_index("ix_research_jobs_status", "research_jobs", ["status"])
    op.create_index("ix_research_jobs_workflow_id", "research_jobs", ["workflow_id"])

    op.create_table(
        "sophia_sessions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_key", sa.String(length=512), nullable=False),
        sa.Column("status", sa.Enum("initializing", "active", "interrupted", "awaiting_handoff", "handed_off", "completed", "cancelled", "failed", name="sophiasessionstatus"), nullable=False),
        sa.Column("channel", sa.Enum("text", "voice", "phone", name="sophiachanneltype"), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=True),
        sa.Column("lead_id", sa.UUID(), nullable=True),
        sa.Column("initiated_by", sa.UUID(), nullable=True),
        sa.Column("channel_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=False),
        sa.Column("turn_count", sa.Integer(), nullable=False),
        sa.Column("max_turns", sa.Integer(), nullable=False),
        sa.Column("checkpoint_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("handoff_to", sa.UUID(), nullable=True),
        sa.Column("handoff_reason", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("handed_off_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["initiated_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_key"),
    )
    op.create_index("ix_sophia_sessions_lead_id", "sophia_sessions", ["lead_id"])
    op.create_index("ix_sophia_sessions_status", "sophia_sessions", ["status"])
    op.create_index("ix_sophia_sessions_workflow_id", "sophia_sessions", ["workflow_id"])

    op.create_table(
        "research_evidence",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("status", sa.Enum("pending", "accepted", "rejected", "duplicate", name="researchevidencestatus"), nullable=False),
        sa.Column("source_uri", sa.Text(), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("content_snippet", sa.Text(), nullable=True),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("citation_ref", sa.Text(), nullable=True),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("snapshot", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_research_evidence_content_hash", "research_evidence", ["content_hash"])
    op.create_index("ix_research_evidence_job_id", "research_evidence", ["job_id"])
    op.create_index("ix_research_evidence_status", "research_evidence", ["status"])

    op.create_table(
        "research_memory",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("task_id", sa.UUID(), nullable=True),
        sa.Column("scope", sa.Enum("job", "task", "session", name="researchmemoryscope"), nullable=False),
        sa.Column("memory_key", sa.String(length=512), nullable=False),
        sa.Column("value", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("job_id", "scope", "memory_key", "task_id", name="uq_research_memory_key"),
    )
    op.create_index("ix_research_memory_expires_at", "research_memory", ["expires_at"])
    op.create_index("ix_research_memory_job_id", "research_memory", ["job_id"])

    op.create_table(
        "research_tasks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("task_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed", "cancelled", "skipped", "blocked", name="researchtaskstatus"), nullable=False),
        sa.Column("task_key", sa.String(length=512), nullable=True),
        sa.Column("task_type", sa.String(length=128), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=False),
        sa.Column("tokens_output", sa.Integer(), nullable=False),
        sa.Column("governance_verdict", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_key"),
    )
    op.create_index("ix_research_tasks_job_id", "research_tasks", ["job_id"])
    op.create_index("ix_research_tasks_status", "research_tasks", ["status"])

    op.create_table(
        "sophia_turns",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("turn_index", sa.Integer(), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "awaiting_approval", "completed", "interrupted", "cancelled", "failed", name="sophiaturnstatus"), nullable=False),
        sa.Column("turn_key", sa.String(length=512), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tool_calls", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("governance_verdict", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=False),
        sa.Column("tokens_output", sa.Integer(), nullable=False),
        sa.Column("interruption_reason", sa.Enum("user_barge_in", "timeout", "governance_block", "tool_approval_required", "handoff_requested", "cancellation", "error", name="sophiainterruptionreason"), nullable=True),
        sa.Column("interruption_notes", sa.Text(), nullable=True),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sophia_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("turn_key"),
    )
    op.create_index("ix_sophia_turns_session_id", "sophia_turns", ["session_id"])
    op.create_index("ix_sophia_turns_status", "sophia_turns", ["status"])

    op.create_table(
        "ai_executions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("execution_key", sa.String(length=512), nullable=False),
        sa.Column("task_type", sa.Enum("inference", "extraction", "scoring", "tool_call", "classification", name="aitasktype"), nullable=False),
        sa.Column("provider", sa.Enum("anthropic", "openai", "bedrock", "noop", name="aiprovidertype"), nullable=False),
        sa.Column("model_name", sa.String(length=256), nullable=False),
        sa.Column("status", sa.Enum("pending", "running", "completed", "failed", "cancelled", "awaiting_approval", name="aiexecutionstatus"), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=True),
        sa.Column("correlation_id", sa.String(length=256), nullable=True),
        sa.Column("input_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("output_payload", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("token_budget", sa.Integer(), nullable=False),
        sa.Column("tokens_used", sa.Integer(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("checkpoint_state", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("requires_approval", sa.Boolean(), nullable=False),
        sa.Column("approval_id", sa.UUID(), nullable=True),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("execution_key"),
    )
    op.create_index("ix_ai_executions_correlation_id", "ai_executions", ["correlation_id"])
    op.create_index("ix_ai_executions_status", "ai_executions", ["status"])
    op.create_index("ix_ai_executions_workflow_id", "ai_executions", ["workflow_id"])

    op.create_table(
        "research_task_dependencies",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("job_id", sa.UUID(), nullable=False),
        sa.Column("upstream_task_id", sa.UUID(), nullable=False),
        sa.Column("downstream_task_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["downstream_task_id"], ["research_tasks.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["job_id"], ["research_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["upstream_task_id"], ["research_tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("upstream_task_id", "downstream_task_id", name="uq_research_task_dep"),
    )
    op.create_index("ix_research_task_dep_downstream", "research_task_dependencies", ["downstream_task_id"])
    op.create_index("ix_research_task_dep_job_id", "research_task_dependencies", ["job_id"])

    op.create_table(
        "workflow_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("step", sa.String(), nullable=False),
        sa.Column("status_at_checkpoint", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id", "step", name="uq_workflow_checkpoints_workflow_step"),
    )
    op.create_index("ix_workflow_checkpoints_workflow_id", "workflow_checkpoints", ["workflow_id"])

    op.create_table(
        "workflow_leases",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("lease_id", sa.UUID(), nullable=False),
        sa.Column("holder", sa.String(length=256), nullable=False),
        sa.Column("acquired_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("renewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Enum("active", "released", "expired", name="leasestatus"), nullable=False),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workflow_id"),
    )
    op.create_index("ix_workflow_leases_expires_at", "workflow_leases", ["expires_at"])
    op.create_index("ix_workflow_leases_status", "workflow_leases", ["status"])

    op.create_table(
        "workflow_snapshots",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workflow_id", sa.UUID(), nullable=False),
        sa.Column("workflow_status", sa.String(length=64), nullable=False),
        sa.Column("current_step", sa.String(), nullable=True),
        sa.Column("state", sa.JSON(), nullable=False),
        sa.Column("captured_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("trigger", sa.String(length=128), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_workflow_snapshots_captured_at", "workflow_snapshots", ["captured_at"])
    op.create_index("ix_workflow_snapshots_workflow_id", "workflow_snapshots", ["workflow_id"])

    op.create_table(
        "transcript_checkpoints",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("transcript_id", sa.UUID(), nullable=False),
        sa.Column("stream_id", sa.UUID(), nullable=True),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("state", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("label", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("transcript_id", "chunk_index", name="uq_transcript_checkpoints_position"),
    )
    op.create_index("ix_transcript_checkpoints_stream_id", "transcript_checkpoints", ["stream_id"])
    op.create_index("ix_transcript_checkpoints_transcript_id", "transcript_checkpoints", ["transcript_id"])

    op.create_table(
        "transcript_streams",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("transcript_id", sa.UUID(), nullable=False),
        sa.Column("stream_key", sa.String(length=512), nullable=False),
        sa.Column("status", sa.Enum("pending", "active", "completed", "interrupted", "cancelled", "failed", name="transcriptstreamstatus"), nullable=False),
        sa.Column("provider", sa.String(length=128), nullable=True),
        sa.Column("model_name", sa.String(length=256), nullable=True),
        sa.Column("tokens_input", sa.Integer(), nullable=False),
        sa.Column("tokens_output", sa.Integer(), nullable=False),
        sa.Column("partial_text", sa.Text(), nullable=True),
        sa.Column("last_chunk_index", sa.Integer(), nullable=True),
        sa.Column("interruption_reason", sa.Text(), nullable=True),
        sa.Column("cancel_reason", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("interrupted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.ForeignKeyConstraint(["transcript_id"], ["transcripts.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stream_key"),
    )
    op.create_index("ix_transcript_streams_status", "transcript_streams", ["status"])
    op.create_index("ix_transcript_streams_transcript_id", "transcript_streams", ["transcript_id"])

    op.create_index(
        "ix_approvals_workflow_pending_type",
        "approvals",
        ["workflow_id", "approval_type"],
        unique=True,
        postgresql_where=sa.text("approval_status = 'pending'"),
    )

    op.add_column("transcripts", sa.Column("source_type", transcript_source_type, nullable=True))
    op.execute("UPDATE transcripts SET source_type = 'call' WHERE source_type IS NULL")
    op.alter_column("transcripts", "source_type", nullable=False)
    op.create_index("ix_transcripts_transcript_status", "transcripts", ["transcript_status"])


def downgrade() -> None:
    op.drop_index("ix_transcripts_transcript_status", table_name="transcripts")
    op.drop_column("transcripts", "source_type")
    postgresql.ENUM(name="transcriptsourcetype").drop(op.get_bind(), checkfirst=True)

    op.drop_index("ix_approvals_workflow_pending_type", table_name="approvals")

    op.drop_index("ix_transcript_streams_transcript_id", table_name="transcript_streams")
    op.drop_index("ix_transcript_streams_status", table_name="transcript_streams")
    op.drop_table("transcript_streams")

    op.drop_index("ix_transcript_checkpoints_transcript_id", table_name="transcript_checkpoints")
    op.drop_index("ix_transcript_checkpoints_stream_id", table_name="transcript_checkpoints")
    op.drop_table("transcript_checkpoints")

    op.drop_index("ix_workflow_snapshots_workflow_id", table_name="workflow_snapshots")
    op.drop_index("ix_workflow_snapshots_captured_at", table_name="workflow_snapshots")
    op.drop_table("workflow_snapshots")

    op.drop_index("ix_workflow_leases_status", table_name="workflow_leases")
    op.drop_index("ix_workflow_leases_expires_at", table_name="workflow_leases")
    op.drop_table("workflow_leases")

    op.drop_index("ix_workflow_checkpoints_workflow_id", table_name="workflow_checkpoints")
    op.drop_table("workflow_checkpoints")

    op.drop_index("ix_research_task_dep_job_id", table_name="research_task_dependencies")
    op.drop_index("ix_research_task_dep_downstream", table_name="research_task_dependencies")
    op.drop_table("research_task_dependencies")

    op.drop_index("ix_ai_executions_workflow_id", table_name="ai_executions")
    op.drop_index("ix_ai_executions_status", table_name="ai_executions")
    op.drop_index("ix_ai_executions_correlation_id", table_name="ai_executions")
    op.drop_table("ai_executions")

    op.drop_index("ix_sophia_turns_status", table_name="sophia_turns")
    op.drop_index("ix_sophia_turns_session_id", table_name="sophia_turns")
    op.drop_table("sophia_turns")

    op.drop_index("ix_research_tasks_status", table_name="research_tasks")
    op.drop_index("ix_research_tasks_job_id", table_name="research_tasks")
    op.drop_table("research_tasks")

    op.drop_index("ix_research_memory_job_id", table_name="research_memory")
    op.drop_index("ix_research_memory_expires_at", table_name="research_memory")
    op.drop_table("research_memory")

    op.drop_index("ix_research_evidence_status", table_name="research_evidence")
    op.drop_index("ix_research_evidence_job_id", table_name="research_evidence")
    op.drop_index("ix_research_evidence_content_hash", table_name="research_evidence")
    op.drop_table("research_evidence")

    op.drop_index("ix_sophia_sessions_workflow_id", table_name="sophia_sessions")
    op.drop_index("ix_sophia_sessions_status", table_name="sophia_sessions")
    op.drop_index("ix_sophia_sessions_lead_id", table_name="sophia_sessions")
    op.drop_table("sophia_sessions")

    op.drop_index("ix_research_jobs_workflow_id", table_name="research_jobs")
    op.drop_index("ix_research_jobs_status", table_name="research_jobs")
    op.drop_index("ix_research_jobs_sophia_session_id", table_name="research_jobs")
    op.drop_table("research_jobs")

    op.drop_index("ix_sophia_events_turn_id", table_name="sophia_events")
    op.drop_index("ix_sophia_events_session_id", table_name="sophia_events")
    op.drop_index("ix_sophia_events_event_type", table_name="sophia_events")
    op.drop_table("sophia_events")

    op.drop_index("ix_research_plans_status", table_name="research_plans")
    op.drop_index("ix_research_plans_job_id", table_name="research_plans")
    op.drop_table("research_plans")

    op.drop_index("ix_research_events_job_id", table_name="research_events")
    op.drop_index("ix_research_events_event_type", table_name="research_events")
    op.drop_index("ix_research_events_emitted_at", table_name="research_events")
    op.drop_table("research_events")

    op.drop_index("ix_governance_policies_status", table_name="governance_policies")
    op.drop_index("ix_governance_policies_risk_tier", table_name="governance_policies")
    op.drop_index("ix_governance_policies_policy_key", table_name="governance_policies")
    op.drop_table("governance_policies")

    op.drop_index("ix_governance_events_policy_id", table_name="governance_events")
    op.drop_index("ix_governance_events_event_type", table_name="governance_events")
    op.drop_index("ix_governance_events_created_at", table_name="governance_events")
    op.drop_index("ix_governance_events_correlation_id", table_name="governance_events")
    op.drop_index("ix_governance_events_approval_id", table_name="governance_events")
    op.drop_table("governance_events")

    op.drop_index("ix_domain_events_event_type", table_name="domain_events")
    op.drop_index("ix_domain_events_channel_seq_num", table_name="domain_events")
    op.drop_table("domain_events")

    op.drop_index("ix_context_snapshots_workflow_id", table_name="context_snapshots")
    op.drop_index("ix_context_snapshots_status", table_name="context_snapshots")
    op.drop_index("ix_context_snapshots_created_at", table_name="context_snapshots")
    op.drop_table("context_snapshots")

    op.drop_index("ix_approval_delegations_status", table_name="approval_delegations")
    op.drop_index("ix_approval_delegations_delegator_id", table_name="approval_delegations")
    op.drop_index("ix_approval_delegations_delegate_id", table_name="approval_delegations")
    op.drop_table("approval_delegations")

