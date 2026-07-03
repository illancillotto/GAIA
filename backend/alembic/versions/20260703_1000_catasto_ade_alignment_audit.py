"""add catasto ade alignment audit tables

Revision ID: 20260703_1000
Revises: 20260630_1100
Create Date: 2026-07-03 10:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260703_1000"
down_revision = "20260630_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cat_ade_alignment_audit_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("ade_run_id", sa.Uuid(), nullable=False),
        sa.Column("execution_mode", sa.String(length=20), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("triggered_by_user_id", sa.Integer(), nullable=True),
        sa.Column("requested_bbox_json", sa.JSON(), nullable=False),
        sa.Column("selected_categories_json", sa.JSON(), nullable=False),
        sa.Column("geometry_threshold_m", sa.Numeric(precision=10, scale=3), nullable=False),
        sa.Column("allow_suppress_missing", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("counters_json", sa.JSON(), nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False, server_default=sa.text("'[]'::json")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["ade_run_id"], ["cat_ade_sync_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["triggered_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_runs_ade_run_id"),
        "cat_ade_alignment_audit_runs",
        ["ade_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_runs_execution_mode"),
        "cat_ade_alignment_audit_runs",
        ["execution_mode"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_runs_status"),
        "cat_ade_alignment_audit_runs",
        ["status"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_runs_triggered_by_user_id"),
        "cat_ade_alignment_audit_runs",
        ["triggered_by_user_id"],
        unique=False,
    )
    op.alter_column("cat_ade_alignment_audit_runs", "allow_suppress_missing", server_default=None)
    op.alter_column("cat_ade_alignment_audit_runs", "warnings_json", server_default=None)

    op.create_table(
        "cat_ade_alignment_audit_changes",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("audit_run_id", sa.Uuid(), nullable=False),
        sa.Column("operation", sa.String(length=30), nullable=False),
        sa.Column("category", sa.String(length=30), nullable=False),
        sa.Column("particella_id", sa.Uuid(), nullable=True),
        sa.Column("comune_id", sa.Uuid(), nullable=True),
        sa.Column("national_cadastral_reference", sa.String(length=80), nullable=True),
        sa.Column("codice_catastale", sa.String(length=4), nullable=True),
        sa.Column("sezione_catastale", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("distance_m", sa.Numeric(precision=12, scale=3), nullable=True),
        sa.Column("before_state_json", sa.JSON(), nullable=True),
        sa.Column("after_state_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["audit_run_id"], ["cat_ade_alignment_audit_runs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["particella_id"], ["cat_particelle.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["comune_id"], ["cat_comuni.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_changes_audit_run_id"),
        "cat_ade_alignment_audit_changes",
        ["audit_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_changes_category"),
        "cat_ade_alignment_audit_changes",
        ["category"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_changes_codice_catastale"),
        "cat_ade_alignment_audit_changes",
        ["codice_catastale"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_changes_foglio"),
        "cat_ade_alignment_audit_changes",
        ["foglio"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_changes_operation"),
        "cat_ade_alignment_audit_changes",
        ["operation"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_changes_particella"),
        "cat_ade_alignment_audit_changes",
        ["particella"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_ade_alignment_audit_changes_particella_id"),
        "cat_ade_alignment_audit_changes",
        ["particella_id"],
        unique=False,
    )
    op.create_index(
        "ix_cat_ade_alignment_audit_changes_parcel_key",
        "cat_ade_alignment_audit_changes",
        ["codice_catastale", "foglio", "particella"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_cat_ade_alignment_audit_changes_parcel_key", table_name="cat_ade_alignment_audit_changes")
    op.drop_index(op.f("ix_cat_ade_alignment_audit_changes_particella_id"), table_name="cat_ade_alignment_audit_changes")
    op.drop_index(op.f("ix_cat_ade_alignment_audit_changes_particella"), table_name="cat_ade_alignment_audit_changes")
    op.drop_index(op.f("ix_cat_ade_alignment_audit_changes_operation"), table_name="cat_ade_alignment_audit_changes")
    op.drop_index(op.f("ix_cat_ade_alignment_audit_changes_foglio"), table_name="cat_ade_alignment_audit_changes")
    op.drop_index(op.f("ix_cat_ade_alignment_audit_changes_codice_catastale"), table_name="cat_ade_alignment_audit_changes")
    op.drop_index(op.f("ix_cat_ade_alignment_audit_changes_category"), table_name="cat_ade_alignment_audit_changes")
    op.drop_index(op.f("ix_cat_ade_alignment_audit_changes_audit_run_id"), table_name="cat_ade_alignment_audit_changes")
    op.drop_table("cat_ade_alignment_audit_changes")

    op.drop_index(
        op.f("ix_cat_ade_alignment_audit_runs_triggered_by_user_id"),
        table_name="cat_ade_alignment_audit_runs",
    )
    op.drop_index(op.f("ix_cat_ade_alignment_audit_runs_status"), table_name="cat_ade_alignment_audit_runs")
    op.drop_index(
        op.f("ix_cat_ade_alignment_audit_runs_execution_mode"),
        table_name="cat_ade_alignment_audit_runs",
    )
    op.drop_index(op.f("ix_cat_ade_alignment_audit_runs_ade_run_id"), table_name="cat_ade_alignment_audit_runs")
    op.drop_table("cat_ade_alignment_audit_runs")
