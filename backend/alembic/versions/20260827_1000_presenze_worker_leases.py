"""Add ownership, lease fencing and fair retry fields to Presenze jobs.

Revision ID: 20260827_1000
Revises: 20260827_0900
"""

import sqlalchemy as sa
from alembic import op

revision = "20260827_1000"
down_revision = "20260827_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("presenze_sync_jobs", sa.Column("worker_id", sa.String(length=128), nullable=True))
    op.add_column("presenze_sync_jobs", sa.Column("lease_token", sa.Uuid(), nullable=True))
    op.add_column(
        "presenze_sync_jobs",
        sa.Column("lease_generation", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column("presenze_sync_jobs", sa.Column("heartbeat_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("presenze_sync_jobs", sa.Column("lease_expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("presenze_sync_jobs", sa.Column("retry_not_before", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "presenze_sync_jobs",
        sa.Column("priority", sa.Integer(), server_default="100", nullable=False),
    )
    op.create_index("ix_presenze_sync_jobs_worker_id", "presenze_sync_jobs", ["worker_id"])
    op.create_index(
        "ix_presenze_sync_jobs_claim",
        "presenze_sync_jobs",
        ["status", "priority", "retry_not_before", "created_at"],
    )
    op.create_index(
        "ix_presenze_sync_jobs_lease_expiry",
        "presenze_sync_jobs",
        ["status", "lease_expires_at"],
    )
    op.alter_column("presenze_sync_jobs", "lease_generation", server_default=None)
    op.alter_column("presenze_sync_jobs", "priority", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_presenze_sync_jobs_lease_expiry", table_name="presenze_sync_jobs")
    op.drop_index("ix_presenze_sync_jobs_claim", table_name="presenze_sync_jobs")
    op.drop_index("ix_presenze_sync_jobs_worker_id", table_name="presenze_sync_jobs")
    for column_name in (
        "priority",
        "retry_not_before",
        "lease_expires_at",
        "heartbeat_at",
        "lease_generation",
        "lease_token",
        "worker_id",
    ):
        op.drop_column("presenze_sync_jobs", column_name)
