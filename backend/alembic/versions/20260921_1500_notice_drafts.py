"""Private SQL artifacts for the draft/confirmation workflow.

Revision ID: 20260921_1500
Revises: 20260918_1500
"""

from alembic import op
import sqlalchemy as sa

revision = "20260921_1500"
down_revision = "20260918_1500"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ruolo_notice_drafts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("source_system", sa.String(40), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), sa.ForeignKey("ruolo_tributi_reminder_batches.id", ondelete="RESTRICT")),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("artifact", sa.LargeBinary(), nullable=False),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("artifact_format", sa.String(8), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("source_system", "source_id", name="uq_notice_draft_source"),
        sa.CheckConstraint("state = 'review_required'", name="ck_notice_draft_state"),
        sa.CheckConstraint("length(artifact_sha256) = 64", name="ck_notice_draft_hash"),
    )
    op.create_index("ix_ruolo_notice_drafts_batch_id", "ruolo_notice_drafts", ["batch_id"])


def downgrade():
    op.drop_index("ix_ruolo_notice_drafts_batch_id", table_name="ruolo_notice_drafts")
    op.drop_table("ruolo_notice_drafts")
