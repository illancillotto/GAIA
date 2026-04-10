"""add wc sync job and operazioni wc fields

Revision ID: 20260410_0038
Revises: 20260410_0037
Create Date: 2026-04-10
"""

from alembic import op
import sqlalchemy as sa


revision = "20260410_0038"
down_revision = "20260410_0037"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "wc_sync_job",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("entity", sa.String(length=50), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_synced", sa.Integer(), nullable=True),
        sa.Column("records_skipped", sa.Integer(), nullable=True),
        sa.Column("records_errors", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.Integer(), nullable=True),
        sa.Column("params_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["triggered_by"], ["application_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_wc_sync_job_entity"), "wc_sync_job", ["entity"], unique=False)
    op.create_index(op.f("ix_wc_sync_job_status"), "wc_sync_job", ["status"], unique=False)

    op.add_column("field_report_category", sa.Column("wc_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_field_report_category_wc_id"), "field_report_category", ["wc_id"], unique=True)

    op.add_column("vehicle", sa.Column("wc_id", sa.Integer(), nullable=True))
    op.add_column("vehicle", sa.Column("wc_vehicle_id", sa.String(length=50), nullable=True))
    op.add_column("vehicle", sa.Column("vehicle_type_wc", sa.String(length=20), nullable=True))
    op.add_column("vehicle", sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_vehicle_wc_id"), "vehicle", ["wc_id"], unique=False)

    op.add_column("vehicle_usage_session", sa.Column("wc_id", sa.Integer(), nullable=True))
    op.add_column("vehicle_usage_session", sa.Column("km_start", sa.Integer(), nullable=True))
    op.add_column("vehicle_usage_session", sa.Column("km_end", sa.Integer(), nullable=True))
    op.add_column("vehicle_usage_session", sa.Column("operator_name", sa.String(length=200), nullable=True))
    op.add_column("vehicle_usage_session", sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_vehicle_usage_session_wc_id"), "vehicle_usage_session", ["wc_id"], unique=False)

    op.add_column("vehicle_fuel_log", sa.Column("wc_id", sa.Integer(), nullable=True))
    op.add_column("vehicle_fuel_log", sa.Column("operator_name", sa.String(length=200), nullable=True))
    op.add_column("vehicle_fuel_log", sa.Column("wc_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_vehicle_fuel_log_wc_id"), "vehicle_fuel_log", ["wc_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_vehicle_fuel_log_wc_id"), table_name="vehicle_fuel_log")
    op.drop_column("vehicle_fuel_log", "wc_synced_at")
    op.drop_column("vehicle_fuel_log", "operator_name")
    op.drop_column("vehicle_fuel_log", "wc_id")

    op.drop_index(op.f("ix_vehicle_usage_session_wc_id"), table_name="vehicle_usage_session")
    op.drop_column("vehicle_usage_session", "wc_synced_at")
    op.drop_column("vehicle_usage_session", "operator_name")
    op.drop_column("vehicle_usage_session", "km_end")
    op.drop_column("vehicle_usage_session", "km_start")
    op.drop_column("vehicle_usage_session", "wc_id")

    op.drop_index(op.f("ix_vehicle_wc_id"), table_name="vehicle")
    op.drop_column("vehicle", "wc_synced_at")
    op.drop_column("vehicle", "vehicle_type_wc")
    op.drop_column("vehicle", "wc_vehicle_id")
    op.drop_column("vehicle", "wc_id")

    op.drop_index(op.f("ix_field_report_category_wc_id"), table_name="field_report_category")
    op.drop_column("field_report_category", "wc_id")

    op.drop_index(op.f("ix_wc_sync_job_status"), table_name="wc_sync_job")
    op.drop_index(op.f("ix_wc_sync_job_entity"), table_name="wc_sync_job")
    op.drop_table("wc_sync_job")
