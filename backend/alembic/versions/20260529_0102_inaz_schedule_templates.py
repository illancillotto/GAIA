"""inaz schedule templates

Revision ID: 20260529_0102
Revises: 20260529_0101
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_0102"
down_revision = "20260529_0101"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "inaz_holidays",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("holiday_date", sa.Date(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("company_code", sa.String(length=32), nullable=True),
        sa.Column("is_workday_override", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("holiday_date", "company_code", "label", name="uq_inaz_holidays_date_company_label"),
    )
    op.create_index(op.f("ix_inaz_holidays_holiday_date"), "inaz_holidays", ["holiday_date"], unique=False)
    op.create_index(op.f("ix_inaz_holidays_company_code"), "inaz_holidays", ["company_code"], unique=False)

    op.create_table(
        "inaz_schedule_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("company_code", sa.String(length=32), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index(op.f("ix_inaz_schedule_templates_code"), "inaz_schedule_templates", ["code"], unique=True)
    op.create_index(op.f("ix_inaz_schedule_templates_company_code"), "inaz_schedule_templates", ["company_code"], unique=False)

    op.create_table(
        "inaz_schedule_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=True),
        sa.Column("weekday", sa.Integer(), nullable=True),
        sa.Column("recurrence_kind", sa.String(length=32), nullable=False, server_default="weekly"),
        sa.Column("week_of_month", sa.Integer(), nullable=True),
        sa.Column("interval_weeks", sa.Integer(), nullable=True),
        sa.Column("anchor_date", sa.Date(), nullable=True),
        sa.Column("start_time", sa.Time(), nullable=False),
        sa.Column("end_time", sa.Time(), nullable=False),
        sa.Column("season_start_month", sa.Integer(), nullable=True),
        sa.Column("season_start_day", sa.Integer(), nullable=True),
        sa.Column("season_end_month", sa.Integer(), nullable=True),
        sa.Column("season_end_day", sa.Integer(), nullable=True),
        sa.Column("applies_on_holiday", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ordinary_label", sa.String(length=64), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["inaz_schedule_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_inaz_schedule_rules_template_id"), "inaz_schedule_rules", ["template_id"], unique=False)

    op.create_table(
        "inaz_collaborator_schedule_assignments",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("collaborator_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["collaborator_id"], ["inaz_collaborators.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["template_id"], ["inaz_schedule_templates.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_inaz_collaborator_schedule_assignments_collaborator_id"),
        "inaz_collaborator_schedule_assignments",
        ["collaborator_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_inaz_collaborator_schedule_assignments_template_id"),
        "inaz_collaborator_schedule_assignments",
        ["template_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_inaz_collaborator_schedule_assignments_template_id"),
        table_name="inaz_collaborator_schedule_assignments",
    )
    op.drop_index(
        op.f("ix_inaz_collaborator_schedule_assignments_collaborator_id"),
        table_name="inaz_collaborator_schedule_assignments",
    )
    op.drop_table("inaz_collaborator_schedule_assignments")
    op.drop_index(op.f("ix_inaz_schedule_rules_template_id"), table_name="inaz_schedule_rules")
    op.drop_table("inaz_schedule_rules")
    op.drop_index(op.f("ix_inaz_schedule_templates_company_code"), table_name="inaz_schedule_templates")
    op.drop_index(op.f("ix_inaz_schedule_templates_code"), table_name="inaz_schedule_templates")
    op.drop_table("inaz_schedule_templates")
    op.drop_index(op.f("ix_inaz_holidays_company_code"), table_name="inaz_holidays")
    op.drop_index(op.f("ix_inaz_holidays_holiday_date"), table_name="inaz_holidays")
    op.drop_table("inaz_holidays")
