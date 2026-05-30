"""Phase 8/9 additions: call runtime, transcript sub-tables, realtime_sessions columns.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-11

Adds:
- call_sessions table
- call_participants table
- call_events table
- transcript_chunks table
- transcript_events table
- realtime_sessions.last_heartbeat_at column
- realtime_sessions.device_info column
- New enum types: callsessionstatus, participantrole, participantstatus,
  transcriptsourcetype, transcriptstreamtype
- Fix transcriptstatus enum (add created, active, paused, archived values)
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None


def upgrade() -> None:
    bind = op.get_bind()

    # -------------------------------------------------------------------------
    # New enum types
    # -------------------------------------------------------------------------
    callsessionstatus_enum = sa.Enum(
        "waiting", "active", "completed", "failed",
        name="callsessionstatus",
        create_type=True,
    )
    participantrole_enum = sa.Enum(
        "operator", "lead", "observer",
        name="participantrole",
        create_type=True,
    )
    participantstatus_enum = sa.Enum(
        "joined", "left", "reconnecting", "dropped",
        name="participantstatus",
        create_type=True,
    )
    transcriptsourcetype_enum = sa.Enum(
        "call", "upload", "realtime", "manual",
        name="transcriptsourcetype",
        create_type=True,
    )
    transcriptstreamtype_enum = sa.Enum(
        "agent", "user", "system", "mixed",
        name="transcriptstreamtype",
        create_type=True,
    )

    for enum in [
        callsessionstatus_enum,
        participantrole_enum,
        participantstatus_enum,
        transcriptsourcetype_enum,
        transcriptstreamtype_enum,
    ]:
        enum.create(bind, checkfirst=True)

    # -------------------------------------------------------------------------
    # Fix transcriptstatus enum — add missing values
    # (PostgreSQL requires ALTER TYPE … ADD VALUE; cannot drop values)
    # -------------------------------------------------------------------------
    for value in ("created", "active", "paused", "archived"):
        bind.execute(sa.text(
            f"ALTER TYPE transcriptstatus ADD VALUE IF NOT EXISTS '{value}'"
        ))

    # -------------------------------------------------------------------------
    # realtime_sessions — add columns
    # -------------------------------------------------------------------------
    op.add_column(
        "realtime_sessions",
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "realtime_sessions",
        sa.Column("device_info", sa.String(), nullable=True),
    )

    # -------------------------------------------------------------------------
    # call_sessions
    # -------------------------------------------------------------------------
    op.create_table(
        "call_sessions",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "call_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("calls.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("session_status", PG_ENUM(name="callsessionstatus", create_type=False), nullable=False),
        sa.Column("correlation_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.create_index("ix_call_sessions_status", "call_sessions", ["session_status"])
    op.create_index("ix_call_sessions_call_id", "call_sessions", ["call_id"])
    op.create_index("ix_call_sessions_correlation_id", "call_sessions", ["correlation_id"])

    # -------------------------------------------------------------------------
    # call_participants
    # -------------------------------------------------------------------------
    op.create_table(
        "call_participants",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("call_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("role", PG_ENUM(name="participantrole", create_type=False), nullable=False),
        sa.Column("participant_status", PG_ENUM(name="participantstatus", create_type=False), nullable=False),
        sa.Column("connection_id", sa.String(), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True),
                  server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.Column("left_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True),
                  server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_call_participants_session_id", "call_participants", ["session_id"])
    op.create_index("ix_call_participants_user_id", "call_participants", ["user_id"])
    op.create_index("ix_call_participants_status", "call_participants", ["participant_status"])
    op.create_index("ix_call_participants_connection_id", "call_participants", ["connection_id"])

    # -------------------------------------------------------------------------
    # call_events (append-only)
    # -------------------------------------------------------------------------
    op.create_table(
        "call_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("call_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("clock_timestamp()"), nullable=False),
    )
    op.create_index("ix_call_events_session_id_sequence", "call_events",
                    ["session_id", "sequence"])
    op.create_index("ix_call_events_event_type", "call_events", ["event_type"])

    # -------------------------------------------------------------------------
    # transcript_chunks (append-only)
    # -------------------------------------------------------------------------
    op.create_table(
        "transcript_chunks",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transcript_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("transcripts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("speaker", sa.String(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("stream_type", PG_ENUM(name="transcriptstreamtype", create_type=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("clock_timestamp()"), nullable=False),
        sa.UniqueConstraint("transcript_id", "chunk_index",
                            name="uq_transcript_chunks_position"),
    )
    op.create_index("ix_transcript_chunks_transcript_id_chunk_index", "transcript_chunks",
                    ["transcript_id", "chunk_index"])

    # -------------------------------------------------------------------------
    # transcript_events (append-only)
    # -------------------------------------------------------------------------
    op.create_table(
        "transcript_events",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "transcript_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("transcripts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True),
                  server_default=sa.text("clock_timestamp()"), nullable=False),
    )
    op.create_index("ix_transcript_events_transcript_id_sequence", "transcript_events",
                    ["transcript_id", "sequence"])
    op.create_index("ix_transcript_events_event_type", "transcript_events", ["event_type"])


def downgrade() -> None:
    # Drop in reverse FK order
    op.drop_index("ix_transcript_events_event_type", table_name="transcript_events")
    op.drop_index("ix_transcript_events_transcript_id_sequence", table_name="transcript_events")
    op.drop_table("transcript_events")

    op.drop_index("ix_transcript_chunks_transcript_id_chunk_index", table_name="transcript_chunks")
    op.drop_table("transcript_chunks")

    op.drop_index("ix_call_events_event_type", table_name="call_events")
    op.drop_index("ix_call_events_session_id_sequence", table_name="call_events")
    op.drop_table("call_events")

    op.drop_index("ix_call_participants_connection_id", table_name="call_participants")
    op.drop_index("ix_call_participants_status", table_name="call_participants")
    op.drop_index("ix_call_participants_user_id", table_name="call_participants")
    op.drop_index("ix_call_participants_session_id", table_name="call_participants")
    op.drop_table("call_participants")

    op.drop_index("ix_call_sessions_correlation_id", table_name="call_sessions")
    op.drop_index("ix_call_sessions_call_id", table_name="call_sessions")
    op.drop_index("ix_call_sessions_status", table_name="call_sessions")
    op.drop_table("call_sessions")

    op.drop_column("realtime_sessions", "device_info")
    op.drop_column("realtime_sessions", "last_heartbeat_at")

    bind = op.get_bind()
    for enum_name in [
        "transcriptstreamtype",
        "transcriptsourcetype",
        "participantstatus",
        "participantrole",
        "callsessionstatus",
    ]:
        sa.Enum(name=enum_name).drop(bind, checkfirst=True)

    # Note: transcriptstatus values (created, active, paused, archived) cannot be
    # removed from PostgreSQL enums without a full type rebuild. Downgrade leaves them.
