"""create inaz bank hours guidance config

Revision ID: 20260624_1900
Revises: 20260624_1600
Create Date: 2026-06-24 19:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260624_1900"
down_revision: str | Sequence[str] | None = "20260624_1600"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "inaz_bank_hours_guidance_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("allow_derived_profile", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("include_overtime_day", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_overtime_night", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_overtime_festive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_overtime_festive_night", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_suggested_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inaz_bank_hours_guidance_config_updated_by_user_id"),
        "inaz_bank_hours_guidance_config",
        ["updated_by_user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_inaz_bank_hours_guidance_config_updated_by_user_id"), table_name="inaz_bank_hours_guidance_config")
    op.drop_table("inaz_bank_hours_guidance_config")
