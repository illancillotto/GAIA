"""Track PostgreSQL-owned outbound runs separately from historical rows."""

import sqlalchemy as sa
from alembic import op

revision = "20261119_1200"
down_revision = "20261107_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "gate_mobile_action_receipt",
        sa.Column("action_id", sa.Text(), primary_key=True),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("acknowledgement", sa.JSON(), nullable=False),
    )
    op.add_column(
        "gate_mobile_sync_run", sa.Column("lease_backend_pid", sa.Integer(), nullable=True)
    )


def downgrade() -> None:
    op.drop_table("gate_mobile_action_receipt")
    op.drop_column("gate_mobile_sync_run", "lease_backend_pid")
