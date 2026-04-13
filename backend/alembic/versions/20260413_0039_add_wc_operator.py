"""add wc operator

Revision ID: 20260413_0039
Revises: 20260410_0038
Create Date: 2026-04-13
"""

from alembic import op
import sqlalchemy as sa


revision = "20260413_0039"
down_revision = "20260410_0038"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wc_operator",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wc_id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=200), nullable=True),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("tax", sa.String(length=20), nullable=True),
        sa.Column("role", sa.String(length=50), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("gaia_user_id", sa.Integer(), nullable=True),
        sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["gaia_user_id"], ["application_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_wc_operator_wc_id"), "wc_operator", ["wc_id"], unique=True)
    op.create_index(op.f("ix_wc_operator_email"), "wc_operator", ["email"], unique=False)
    op.create_index(op.f("ix_wc_operator_tax"), "wc_operator", ["tax"], unique=False)
    op.create_index(op.f("ix_wc_operator_role"), "wc_operator", ["role"], unique=False)
    op.create_index(op.f("ix_wc_operator_gaia_user_id"), "wc_operator", ["gaia_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_wc_operator_gaia_user_id"), table_name="wc_operator")
    op.drop_index(op.f("ix_wc_operator_role"), table_name="wc_operator")
    op.drop_index(op.f("ix_wc_operator_tax"), table_name="wc_operator")
    op.drop_index(op.f("ix_wc_operator_email"), table_name="wc_operator")
    op.drop_index(op.f("ix_wc_operator_wc_id"), table_name="wc_operator")
    op.drop_table("wc_operator")
