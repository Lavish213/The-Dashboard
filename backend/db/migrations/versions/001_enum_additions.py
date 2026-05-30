"""add mode_changed and requires_approval enum values

Revision ID: 001_enum_additions
Revises:
Create Date: 2025-05-30
"""
from alembic import op

revision = "001_enum_additions"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TYPE sophiaeventtype ADD VALUE IF NOT EXISTS 'mode_changed'")
    op.execute("ALTER TYPE actionclassification ADD VALUE IF NOT EXISTS 'requires_approval'")


def downgrade() -> None:
    pass
