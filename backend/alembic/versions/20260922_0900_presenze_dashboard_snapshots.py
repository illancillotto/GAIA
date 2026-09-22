"""Add persisted monthly Presenze dashboard snapshots."""

import sqlalchemy as sa

from alembic import op

revision = "20260922_0900"
down_revision = "20260921_2000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presenze_dashboard_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column(
            "source_sync_job_id",
            sa.Uuid(),
            sa.ForeignKey("presenze_sync_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "period_start", "period_end", name="uq_presenze_dashboard_snapshots_period"
        ),
    )
    op.create_index(
        "ix_presenze_dashboard_snapshots_period_start",
        "presenze_dashboard_snapshots",
        ["period_start"],
    )
    op.create_index(
        "ix_presenze_dashboard_snapshots_period_end", "presenze_dashboard_snapshots", ["period_end"]
    )
    op.create_index(
        "ix_presenze_dashboard_snapshots_source_sync_job_id",
        "presenze_dashboard_snapshots",
        ["source_sync_job_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_presenze_dashboard_snapshots_source_sync_job_id",
        table_name="presenze_dashboard_snapshots",
    )
    op.drop_index(
        "ix_presenze_dashboard_snapshots_period_end", table_name="presenze_dashboard_snapshots"
    )
    op.drop_index(
        "ix_presenze_dashboard_snapshots_period_start", table_name="presenze_dashboard_snapshots"
    )
    op.drop_table("presenze_dashboard_snapshots")
