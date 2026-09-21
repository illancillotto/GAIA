"""Persist atomically confirmed notice generations.

Revision ID: 20260921_2000
Revises: 20260921_1900
"""

from alembic import op
import sqlalchemy as sa

revision = "20260921_2000"
down_revision = "20260921_1900"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ruolo_notice_generation_confirmations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("generation_id", sa.Uuid(), nullable=False),
        sa.Column("generation_kind", sa.String(16), nullable=False),
        sa.Column("review_digest", sa.String(64), nullable=False),
        sa.Column("input_basis", sa.JSON(), nullable=False),
        sa.Column("identity_keys", sa.JSON(), nullable=False),
        sa.Column("notice_numbers", sa.JSON(), nullable=False),
        sa.Column(
            "confirmed_by",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "confirmed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint(
            "generation_id", "generation_kind", name="uq_notice_generation_confirmation_source"
        ),
    )
    op.create_index(
        "ix_ruolo_notice_generation_confirmations_generation_id",
        "ruolo_notice_generation_confirmations",
        ["generation_id"],
    )


def downgrade():
    op.drop_index(
        "ix_ruolo_notice_generation_confirmations_generation_id",
        table_name="ruolo_notice_generation_confirmations",
    )
    op.drop_table("ruolo_notice_generation_confirmations")
