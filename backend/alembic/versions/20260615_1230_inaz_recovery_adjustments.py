"""add inaz recovery adjustments

Revision ID: 20260615_1230
Revises: 20260615_1200
Create Date: 2026-06-15 12:30:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260615_1230"
down_revision = "20260615_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inaz_recovery_adjustments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("collaborator_id", sa.Uuid(), nullable=False),
        sa.Column("adjustment_date", sa.Date(), nullable=False),
        sa.Column("delta_days", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("approval_status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("approval_note", sa.Text(), nullable=True),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["collaborator_id"], ["inaz_collaborators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inaz_recovery_adjustments_collaborator_id"), "inaz_recovery_adjustments", ["collaborator_id"], unique=False)
    op.create_index(op.f("ix_inaz_recovery_adjustments_adjustment_date"), "inaz_recovery_adjustments", ["adjustment_date"], unique=False)
    op.create_index(op.f("ix_inaz_recovery_adjustments_kind"), "inaz_recovery_adjustments", ["kind"], unique=False)
    op.create_index(op.f("ix_inaz_recovery_adjustments_approval_status"), "inaz_recovery_adjustments", ["approval_status"], unique=False)
    op.create_index(op.f("ix_inaz_recovery_adjustments_created_by_user_id"), "inaz_recovery_adjustments", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_inaz_recovery_adjustments_reviewed_by_user_id"), "inaz_recovery_adjustments", ["reviewed_by_user_id"], unique=False)
    op.create_index(op.f("ix_inaz_recovery_adjustments_updated_by_user_id"), "inaz_recovery_adjustments", ["updated_by_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inaz_recovery_adjustments_updated_by_user_id"), table_name="inaz_recovery_adjustments")
    op.drop_index(op.f("ix_inaz_recovery_adjustments_reviewed_by_user_id"), table_name="inaz_recovery_adjustments")
    op.drop_index(op.f("ix_inaz_recovery_adjustments_created_by_user_id"), table_name="inaz_recovery_adjustments")
    op.drop_index(op.f("ix_inaz_recovery_adjustments_approval_status"), table_name="inaz_recovery_adjustments")
    op.drop_index(op.f("ix_inaz_recovery_adjustments_kind"), table_name="inaz_recovery_adjustments")
    op.drop_index(op.f("ix_inaz_recovery_adjustments_adjustment_date"), table_name="inaz_recovery_adjustments")
    op.drop_index(op.f("ix_inaz_recovery_adjustments_collaborator_id"), table_name="inaz_recovery_adjustments")
    op.drop_table("inaz_recovery_adjustments")
