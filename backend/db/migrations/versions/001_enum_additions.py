"""add mode_changed and requires_approval enum values if types exist

Revision ID: 001_enum_additions
Revises:
Create Date: 2025-05-30
"""
from alembic import op
from sqlalchemy import text

revision = "001_enum_additions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    row = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'sophiaeventtype'")).fetchone()
    if row:
        conn.execute(text("ALTER TYPE sophiaeventtype ADD VALUE IF NOT EXISTS 'mode_changed'"))

    row2 = conn.execute(text("SELECT 1 FROM pg_type WHERE typname = 'actionclassification'")).fetchone()
    if row2:
        conn.execute(text("ALTER TYPE actionclassification ADD VALUE IF NOT EXISTS 'requires_approval'"))


def downgrade() -> None:
    pass
