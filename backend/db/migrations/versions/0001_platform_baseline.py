import json
from pathlib import Path

from alembic import op

revision = "0001_platform_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    snapshot = json.loads(Path(__file__).with_suffix(".json").read_text())
    for statement in snapshot["upgrade"]:
        op.execute(statement)


def downgrade():
    snapshot = json.loads(Path(__file__).with_suffix(".json").read_text())
    for statement in snapshot["downgrade"]:
        op.execute(statement)
