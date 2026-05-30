"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-11

"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def _create_enum(bind, name: str, *values: str) -> None:
    """Create enum idempotently via PL/pgSQL exception handler (asyncpg-safe)."""
    vals = ", ".join(f"'{v}'" for v in values)
    bind.execute(sa.text(f"""
        DO $$ BEGIN
            CREATE TYPE {name} AS ENUM ({vals});
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """))


def _ref(name: str) -> PG_ENUM:
    """Reference-only enum — type must already exist in DB, no CREATE TYPE triggered."""
    return PG_ENUM(name=name, create_type=False)


def upgrade() -> None:
    # ---------------------------------------------------------------------------
    # Create PostgreSQL native enum types (idempotent, before any table creation)
    # ---------------------------------------------------------------------------
    bind = op.get_bind()
    _create_enum(bind, "userrole", "admin", "operator", "reviewer")
    _create_enum(bind, "userstatus", "active", "inactive", "suspended")
    _create_enum(bind, "leadstatus", "new", "contacted", "qualified",
                 "disqualified", "converted", "dead")
    _create_enum(bind, "leadsource", "organic", "paid", "referral", "direct", "imported")
    _create_enum(bind, "propertystatus", "active", "under_contract", "sold", "withdrawn")
    _create_enum(bind, "workflowtype", "outreach", "qualification", "follow_up", "closing")
    _create_enum(bind, "workflowstatus", "pending", "active", "paused",
                 "completed", "failed", "cancelled")
    _create_enum(bind, "approvaltype", "offer", "price_reduction", "skip_trace", "outreach")
    _create_enum(bind, "approvalstatus", "pending", "approved", "rejected", "expired", "escalated")
    _create_enum(bind, "risklevel", "low", "medium", "high", "critical")
    _create_enum(bind, "transcriptstatus", "pending", "processing", "completed", "failed")
    _create_enum(bind, "callstatus", "initiated", "ringing", "connected",
                 "completed", "failed", "no_answer", "voicemail")
    _create_enum(bind, "callprovider", "twilio", "retell", "bland")
    _create_enum(bind, "decisiontype", "qualification", "recommendation", "extraction", "scoring")
    _create_enum(bind, "realtimesessionstatus", "connected", "disconnected", "expired")
    _create_enum(bind, "notificationtype", "approval_required", "workflow_update",
                 "system_alert", "lead_activity")
    _create_enum(bind, "auditactortype", "user", "system", "ai")

    # ---------------------------------------------------------------------------
    # 1. users
    # ---------------------------------------------------------------------------
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("hashed_password", sa.String(), nullable=True),
        sa.Column("full_name", sa.String(), nullable=True),
        sa.Column("role", _ref("userrole"), nullable=False),
        sa.Column("status", _ref("userstatus"), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ---------------------------------------------------------------------------
    # 2. properties
    # ---------------------------------------------------------------------------
    op.create_table(
        "properties",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("address", sa.String(), nullable=False),
        sa.Column("city", sa.String(), nullable=False),
        sa.Column("state", sa.String(2), nullable=False),
        sa.Column("zip", sa.String(10), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("estimated_value", sa.Integer(), nullable=True),
        sa.Column("property_status", _ref("propertystatus"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_properties_city", "properties", ["city"])
    op.create_index("ix_properties_state", "properties", ["state"])
    op.create_index("ix_properties_property_status", "properties", ["property_status"])
    op.create_index("ix_properties_city_state", "properties", ["city", "state"])

    # ---------------------------------------------------------------------------
    # 3. leads (FK -> users, properties)
    # ---------------------------------------------------------------------------
    op.create_table(
        "leads",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("lead_status", _ref("leadstatus"), nullable=False),
        sa.Column("lead_source", _ref("leadsource"), nullable=True),
        sa.Column(
            "assigned_user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "property_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("properties.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("ai_score", sa.Integer(), nullable=True),
        sa.Column("last_contacted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_leads_phone", "leads", ["phone"])
    op.create_index("ix_leads_lead_status", "leads", ["lead_status"])
    op.create_index("ix_leads_assigned_user_id", "leads", ["assigned_user_id"])
    op.create_index("ix_leads_property_id", "leads", ["property_id"])

    # ---------------------------------------------------------------------------
    # 4. workflows (FK -> leads, users)
    # ---------------------------------------------------------------------------
    op.create_table(
        "workflows",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("workflow_type", _ref("workflowtype"), nullable=False),
        sa.Column("workflow_status", _ref("workflowstatus"), nullable=False),
        sa.Column("current_step", sa.String(), nullable=True),
        sa.Column("correlation_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "lead_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "initiated_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_workflows_workflow_type", "workflows", ["workflow_type"])
    op.create_index("ix_workflows_workflow_status", "workflows", ["workflow_status"])
    op.create_index("ix_workflows_correlation_id", "workflows", ["correlation_id"], unique=True)
    op.create_index("ix_workflows_lead_id", "workflows", ["lead_id"])

    # ---------------------------------------------------------------------------
    # 5. workflow_events (FK -> workflows)
    # ---------------------------------------------------------------------------
    op.create_table(
        "workflow_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("causation_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_type", _ref("auditactortype"), nullable=False),
        sa.Column("actor_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_workflow_events_workflow_id", "workflow_events", ["workflow_id"])
    op.create_index("ix_workflow_events_event_type", "workflow_events", ["event_type"])
    op.create_index("ix_workflow_events_correlation_id", "workflow_events", ["correlation_id"])
    op.create_index(
        "ix_workflow_events_workflow_id_created_at",
        "workflow_events", ["workflow_id", "created_at"],
    )

    # ---------------------------------------------------------------------------
    # 6. approvals (FK -> workflows, users x2)
    # ---------------------------------------------------------------------------
    op.create_table(
        "approvals",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("approval_type", _ref("approvaltype"), nullable=False),
        sa.Column("approval_status", _ref("approvalstatus"), nullable=False),
        sa.Column(
            "requested_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "resolved_by",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("risk_level", _ref("risklevel"), nullable=False),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_approvals_workflow_id", "approvals", ["workflow_id"])
    op.create_index("ix_approvals_approval_status", "approvals", ["approval_status"])

    # ---------------------------------------------------------------------------
    # 7. calls (FK -> leads, workflows)
    # ---------------------------------------------------------------------------
    op.create_table(
        "calls",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "workflow_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("provider", _ref("callprovider"), nullable=False),
        sa.Column("call_status", _ref("callstatus"), nullable=False),
        sa.Column("provider_call_id", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("recording_url", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_calls_lead_id", "calls", ["lead_id"])
    op.create_index("ix_calls_workflow_id", "calls", ["workflow_id"])
    op.create_index("ix_calls_call_status", "calls", ["call_status"])

    # ---------------------------------------------------------------------------
    # 8. transcripts (FK -> leads, workflows, calls)
    # ---------------------------------------------------------------------------
    op.create_table(
        "transcripts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "lead_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("leads.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "workflow_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "call_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("transcript_status", _ref("transcriptstatus"), nullable=False),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("duration_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_transcripts_lead_id", "transcripts", ["lead_id"])
    op.create_index("ix_transcripts_workflow_id", "transcripts", ["workflow_id"])
    op.create_index("ix_transcripts_call_id", "transcripts", ["call_id"])

    # ---------------------------------------------------------------------------
    # 9. transcript_segments (FK -> transcripts)
    # ---------------------------------------------------------------------------
    op.create_table(
        "transcript_segments",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transcript_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("transcripts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("speaker", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=False),
        sa.Column("end_ms", sa.Integer(), nullable=False),
        sa.Column("sentiment", sa.String(), nullable=True),
        sa.Column("emotion", sa.String(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_transcript_segments_transcript_id", "transcript_segments", ["transcript_id"])
    op.create_index("ix_transcript_segments_speaker", "transcript_segments", ["speaker"])
    op.create_index("ix_transcript_segments_start_ms", "transcript_segments", ["start_ms"])
    op.create_index(
        "ix_transcript_segments_transcript_id_start_ms",
        "transcript_segments", ["transcript_id", "start_ms"],
    )

    # ---------------------------------------------------------------------------
    # 10. ai_decisions (FK -> workflows, transcripts)
    # ---------------------------------------------------------------------------
    op.create_table(
        "ai_decisions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "workflow_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("workflows.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "transcript_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("transcripts.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decision_type", _ref("decisiontype"), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=True),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("model_name", sa.String(), nullable=True),
        sa.Column("input_summary", sa.Text(), nullable=True),
        sa.Column("output_summary", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_ai_decisions_workflow_id", "ai_decisions", ["workflow_id"])
    op.create_index("ix_ai_decisions_transcript_id", "ai_decisions", ["transcript_id"])
    op.create_index("ix_ai_decisions_decision_type", "ai_decisions", ["decision_type"])

    # ---------------------------------------------------------------------------
    # 11. realtime_sessions (FK -> users)
    # ---------------------------------------------------------------------------
    op.create_table(
        "realtime_sessions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("socket_id", sa.String(), nullable=False),
        sa.Column("session_status", _ref("realtimesessionstatus"), nullable=False),
        sa.Column("connected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("disconnected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_realtime_sessions_user_id", "realtime_sessions", ["user_id"])
    op.create_index("ix_realtime_sessions_session_status", "realtime_sessions", ["session_status"])

    # ---------------------------------------------------------------------------
    # 12. notifications (FK -> users)
    # ---------------------------------------------------------------------------
    op.create_table(
        "notifications",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("notification_type", _ref("notificationtype"), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_notifications_user_id", "notifications", ["user_id"])
    op.create_index("ix_notifications_read_at", "notifications", ["read_at"])

    # ---------------------------------------------------------------------------
    # 13. audit_logs (no FK deps)
    # ---------------------------------------------------------------------------
    op.create_table(
        "audit_logs",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column("actor_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_type", _ref("auditactortype"), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("target_type", sa.String(), nullable=False),
        sa.Column("target_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("correlation_id", sa.UUID(as_uuid=True), nullable=True),
        sa.Column("ip_address", sa.String(), nullable=True),
        sa.Column("user_agent", sa.String(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_audit_logs_actor_id", "audit_logs", ["actor_id"])
    op.create_index("ix_audit_logs_actor_type", "audit_logs", ["actor_type"])
    op.create_index("ix_audit_logs_target_type", "audit_logs", ["target_type"])
    op.create_index("ix_audit_logs_target_id", "audit_logs", ["target_id"])
    op.create_index("ix_audit_logs_correlation_id", "audit_logs", ["correlation_id"])
    op.create_index("ix_audit_logs_actor_id_created_at", "audit_logs", ["actor_id", "created_at"])
    op.create_index("ix_audit_logs_target_type_target_id", "audit_logs", ["target_type", "target_id"])


def downgrade() -> None:
    op.drop_index("ix_audit_logs_target_type_target_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id_created_at", table_name="audit_logs")
    op.drop_index("ix_audit_logs_correlation_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target_id", table_name="audit_logs")
    op.drop_index("ix_audit_logs_target_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_type", table_name="audit_logs")
    op.drop_index("ix_audit_logs_actor_id", table_name="audit_logs")

    op.drop_index("ix_notifications_read_at", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")

    op.drop_index("ix_realtime_sessions_session_status", table_name="realtime_sessions")
    op.drop_index("ix_realtime_sessions_user_id", table_name="realtime_sessions")

    op.drop_index("ix_ai_decisions_decision_type", table_name="ai_decisions")
    op.drop_index("ix_ai_decisions_transcript_id", table_name="ai_decisions")
    op.drop_index("ix_ai_decisions_workflow_id", table_name="ai_decisions")

    op.drop_index("ix_transcript_segments_transcript_id_start_ms", table_name="transcript_segments")
    op.drop_index("ix_transcript_segments_start_ms", table_name="transcript_segments")
    op.drop_index("ix_transcript_segments_speaker", table_name="transcript_segments")
    op.drop_index("ix_transcript_segments_transcript_id", table_name="transcript_segments")

    op.drop_index("ix_transcripts_call_id", table_name="transcripts")
    op.drop_index("ix_transcripts_workflow_id", table_name="transcripts")
    op.drop_index("ix_transcripts_lead_id", table_name="transcripts")

    op.drop_index("ix_calls_call_status", table_name="calls")
    op.drop_index("ix_calls_workflow_id", table_name="calls")
    op.drop_index("ix_calls_lead_id", table_name="calls")

    op.drop_index("ix_approvals_approval_status", table_name="approvals")
    op.drop_index("ix_approvals_workflow_id", table_name="approvals")

    op.drop_index("ix_workflow_events_workflow_id_created_at", table_name="workflow_events")
    op.drop_index("ix_workflow_events_correlation_id", table_name="workflow_events")
    op.drop_index("ix_workflow_events_event_type", table_name="workflow_events")
    op.drop_index("ix_workflow_events_workflow_id", table_name="workflow_events")

    op.drop_index("ix_workflows_lead_id", table_name="workflows")
    op.drop_index("ix_workflows_correlation_id", table_name="workflows")
    op.drop_index("ix_workflows_workflow_status", table_name="workflows")
    op.drop_index("ix_workflows_workflow_type", table_name="workflows")

    op.drop_index("ix_leads_property_id", table_name="leads")
    op.drop_index("ix_leads_assigned_user_id", table_name="leads")
    op.drop_index("ix_leads_lead_status", table_name="leads")
    op.drop_index("ix_leads_phone", table_name="leads")

    op.drop_index("ix_properties_city_state", table_name="properties")
    op.drop_index("ix_properties_property_status", table_name="properties")
    op.drop_index("ix_properties_state", table_name="properties")
    op.drop_index("ix_properties_city", table_name="properties")

    op.drop_index("ix_users_email", table_name="users")

    op.drop_table("audit_logs")
    op.drop_table("notifications")
    op.drop_table("realtime_sessions")
    op.drop_table("ai_decisions")
    op.drop_table("transcript_segments")
    op.drop_table("transcripts")
    op.drop_table("calls")
    op.drop_table("approvals")
    op.drop_table("workflow_events")
    op.drop_table("workflows")
    op.drop_table("leads")
    op.drop_table("properties")
    op.drop_table("users")

    bind = op.get_bind()
    for enum_name in [
        "auditactortype",
        "notificationtype",
        "realtimesessionstatus",
        "decisiontype",
        "transcriptstatus",
        "callstatus",
        "callprovider",
        "risklevel",
        "approvalstatus",
        "approvaltype",
        "workflowstatus",
        "workflowtype",
        "propertystatus",
        "leadsource",
        "leadstatus",
        "userstatus",
        "userrole",
    ]:
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)
