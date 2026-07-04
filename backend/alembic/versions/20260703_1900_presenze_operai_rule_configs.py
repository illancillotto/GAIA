"""add presenze operai rule configs

Revision ID: 20260703_1900
Revises: 20260703_1000
Create Date: 2026-07-03 19:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260703_1900"
down_revision = "20260703_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("presenze_collaborators", sa.Column("operai_group", sa.String(length=32), nullable=True))
    op.create_index(op.f("ix_presenze_collaborators_operai_group"), "presenze_collaborators", ["operai_group"], unique=False)

    op.create_table(
        "presenze_operai_rule_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("operai_group", sa.String(length=32), nullable=True),
        sa.Column("weekday_schedule_codes", sa.JSON(), nullable=False),
        sa.Column("saturday_schedule_codes", sa.JSON(), nullable=False),
        sa.Column("saturday_week_ordinals", sa.JSON(), nullable=False),
        sa.Column("weekday_expected_minutes", sa.Integer(), nullable=False),
        sa.Column("saturday_expected_minutes", sa.Integer(), nullable=False),
        sa.Column("missing_tolerance_minutes", sa.Integer(), nullable=False),
        sa.Column("mpe_review_threshold_minutes", sa.Integer(), nullable=False),
        sa.Column("allowed_absence_causes", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_presenze_operai_rule_configs_code"), "presenze_operai_rule_configs", ["code"], unique=True)
    op.create_index(op.f("ix_presenze_operai_rule_configs_is_active"), "presenze_operai_rule_configs", ["is_active"], unique=False)
    op.create_index(op.f("ix_presenze_operai_rule_configs_operai_group"), "presenze_operai_rule_configs", ["operai_group"], unique=False)
    op.alter_column("presenze_operai_rule_configs", "is_active", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_presenze_operai_rule_configs_operai_group"), table_name="presenze_operai_rule_configs")
    op.drop_index(op.f("ix_presenze_operai_rule_configs_is_active"), table_name="presenze_operai_rule_configs")
    op.drop_index(op.f("ix_presenze_operai_rule_configs_code"), table_name="presenze_operai_rule_configs")
    op.drop_table("presenze_operai_rule_configs")

    op.drop_index(op.f("ix_presenze_collaborators_operai_group"), table_name="presenze_collaborators")
    op.drop_column("presenze_collaborators", "operai_group")
