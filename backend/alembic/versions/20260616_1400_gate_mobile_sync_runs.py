"""add gate mobile sync run audit table

Revision ID: 20260616_1400
Revises: 20260615_1300
Create Date: 2026-06-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_1400"
down_revision: Union[str, None] = "20260615_1300"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "gate_mobile_sync_run",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("trigger_source", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("requested_tasks_count", sa.Integer(), nullable=False),
        sa.Column("operators_pushed", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("requested_tasks_json", sa.JSON(), nullable=True),
        sa.Column("error_kind", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_gate_mobile_sync_run_error_kind", "gate_mobile_sync_run", ["error_kind"], unique=False)
    op.create_index("ix_gate_mobile_sync_run_status", "gate_mobile_sync_run", ["status"], unique=False)
    op.create_index("ix_gate_mobile_sync_run_trigger_source", "gate_mobile_sync_run", ["trigger_source"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_gate_mobile_sync_run_trigger_source", table_name="gate_mobile_sync_run")
    op.drop_index("ix_gate_mobile_sync_run_status", table_name="gate_mobile_sync_run")
    op.drop_index("ix_gate_mobile_sync_run_error_kind", table_name="gate_mobile_sync_run")
    op.drop_table("gate_mobile_sync_run")
