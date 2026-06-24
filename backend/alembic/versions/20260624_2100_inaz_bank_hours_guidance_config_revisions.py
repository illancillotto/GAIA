"""inaz bank hours guidance config revisions

Revision ID: 20260624_2100
Revises: 20260624_1900
Create Date: 2026-06-24 21:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "20260624_2100"
down_revision = "20260624_1900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inaz_bank_hours_guidance_config_revisions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("config_id", sa.Integer(), nullable=False),
        sa.Column("allow_derived_profile", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("include_overtime_day", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_overtime_night", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_overtime_festive", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("include_overtime_festive_night", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("min_suggested_minutes", sa.Integer(), nullable=False, server_default="60"),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("changed_by_user_id", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["changed_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["config_id"], ["inaz_bank_hours_guidance_config.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_inaz_bank_hours_guidance_config_revisions_changed_at",
        "inaz_bank_hours_guidance_config_revisions",
        ["changed_at"],
        unique=False,
    )
    op.create_index(
        "ix_inaz_bank_hours_guidance_config_revisions_changed_by_user_id",
        "inaz_bank_hours_guidance_config_revisions",
        ["changed_by_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_inaz_bank_hours_guidance_config_revisions_config_id",
        "inaz_bank_hours_guidance_config_revisions",
        ["config_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_inaz_bank_hours_guidance_config_revisions_config_id", table_name="inaz_bank_hours_guidance_config_revisions")
    op.drop_index(
        "ix_inaz_bank_hours_guidance_config_revisions_changed_by_user_id",
        table_name="inaz_bank_hours_guidance_config_revisions",
    )
    op.drop_index("ix_inaz_bank_hours_guidance_config_revisions_changed_at", table_name="inaz_bank_hours_guidance_config_revisions")
    op.drop_table("inaz_bank_hours_guidance_config_revisions")
