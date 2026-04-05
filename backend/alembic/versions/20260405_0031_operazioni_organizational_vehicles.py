"""operazioni module — organizational and vehicle domain tables

Revision ID: 20260405_0031
Revises: 20260405_0030
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260405_0031"
down_revision = "20260405_0030"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. team
    op.create_table(
        "team",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "supervisor_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
    )
    op.create_index("idx_team_name", "team", ["name"])
    op.create_index("idx_team_supervisor_user_id", "team", ["supervisor_user_id"])
    op.create_index("idx_team_code", "team", ["code"])

    # 2. team_membership
    op.create_table(
        "team_membership",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role_in_team", sa.String(100), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=False),
        sa.Column("valid_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_primary", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_team_membership_validity",
        ),
    )
    op.create_index("idx_team_membership_team_id", "team_membership", ["team_id"])
    op.create_index("idx_team_membership_user_id", "team_membership", ["user_id"])
    op.create_index(
        "idx_team_membership_validity", "team_membership", ["valid_from", "valid_to"]
    )

    # 3. operator_profile
    op.create_table(
        "operator_profile",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id", ondelete="CASCADE"),
            unique=True,
            nullable=False,
        ),
        sa.Column("employee_code", sa.String(50), unique=True, nullable=True),
        sa.Column("phone", sa.String(50), nullable=True),
        sa.Column(
            "can_drive_vehicles", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("idx_operator_profile_user_id", "operator_profile", ["user_id"])

    # 4. vehicle
    op.create_table(
        "vehicle",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("plate_number", sa.String(20), unique=True, nullable=True),
        sa.Column("asset_tag", sa.String(100), unique=True, nullable=True),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("vehicle_type", sa.String(100), nullable=False),
        sa.Column("brand", sa.String(100), nullable=True),
        sa.Column("model", sa.String(100), nullable=True),
        sa.Column("year_of_manufacture", sa.Integer, nullable=True),
        sa.Column("fuel_type", sa.String(50), nullable=True),
        sa.Column(
            "current_status", sa.String(50), nullable=False, server_default="available"
        ),
        sa.Column("ownership_type", sa.String(50), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("gps_provider_code", sa.String(100), nullable=True),
        sa.Column(
            "has_gps_device", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
    )
    op.create_index("idx_vehicle_name", "vehicle", ["name"])
    op.create_index("idx_vehicle_current_status", "vehicle", ["current_status"])
    op.create_index("idx_vehicle_vehicle_type", "vehicle", ["vehicle_type"])
    op.create_index("idx_vehicle_code", "vehicle", ["code"])

    # 5. vehicle_assignment
    op.create_table(
        "vehicle_assignment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("assignment_target_type", sa.String(20), nullable=False),
        sa.Column(
            "operator_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team.id"),
            nullable=True,
        ),
        sa.Column(
            "assigned_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("reason", sa.Text, nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "assignment_target_type IN ('operator','team')",
            name="ck_vehicle_assignment_target_type",
        ),
        sa.CheckConstraint(
            "end_at IS NULL OR end_at >= start_at", name="ck_vehicle_assignment_dates"
        ),
    )
    op.create_index(
        "idx_vehicle_assignment_vehicle_id", "vehicle_assignment", ["vehicle_id"]
    )
    op.create_index(
        "idx_vehicle_assignment_operator_user_id",
        "vehicle_assignment",
        ["operator_user_id"],
    )
    op.create_index("idx_vehicle_assignment_team_id", "vehicle_assignment", ["team_id"])
    op.create_index(
        "idx_vehicle_assignment_start_at", "vehicle_assignment", ["start_at"]
    )

    # 6. vehicle_usage_session (MUST be before odometer and fuel_log)
    op.create_table(
        "vehicle_usage_session",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "started_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.Column(
            "actual_driver_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team.id"),
            nullable=True,
        ),
        sa.Column(
            "related_assignment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_assignment.id"),
            nullable=True,
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_odometer_km", sa.Numeric(12, 3), nullable=False),
        sa.Column("end_odometer_km", sa.Numeric(12, 3), nullable=True),
        sa.Column("start_latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("start_longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("end_latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("end_longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("gps_source", sa.String(30), nullable=True),
        sa.Column("route_distance_km", sa.Numeric(12, 3), nullable=True),
        sa.Column("engine_hours", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column(
            "validated_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "ended_at IS NULL OR ended_at >= started_at", name="ck_usage_session_dates"
        ),
        sa.CheckConstraint(
            "start_odometer_km >= 0", name="ck_usage_session_start_odometer"
        ),
        sa.CheckConstraint(
            "end_odometer_km IS NULL OR end_odometer_km >= start_odometer_km",
            name="ck_usage_session_end_odometer",
        ),
    )
    op.create_index(
        "idx_vehicle_usage_session_vehicle_id", "vehicle_usage_session", ["vehicle_id"]
    )
    op.create_index(
        "idx_vehicle_usage_session_started_by_user_id",
        "vehicle_usage_session",
        ["started_by_user_id"],
    )
    op.create_index(
        "idx_vehicle_usage_session_actual_driver_user_id",
        "vehicle_usage_session",
        ["actual_driver_user_id"],
    )
    op.create_index(
        "idx_vehicle_usage_session_team_id", "vehicle_usage_session", ["team_id"]
    )
    op.create_index(
        "idx_vehicle_usage_session_started_at", "vehicle_usage_session", ["started_at"]
    )
    op.create_index(
        "idx_vehicle_usage_session_status", "vehicle_usage_session", ["status"]
    )

    # 7. vehicle_odometer_reading (FK to vehicle_usage_session — now exists)
    op.create_table(
        "vehicle_odometer_reading",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reading_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("odometer_km", sa.Numeric(12, 3), nullable=False),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column(
            "usage_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_usage_session.id"),
            nullable=True,
        ),
        sa.Column(
            "recorded_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("odometer_km >= 0", name="ck_odometer_km_positive"),
    )
    op.create_index(
        "idx_vehicle_odometer_vehicle_id", "vehicle_odometer_reading", ["vehicle_id"]
    )
    op.create_index(
        "idx_vehicle_odometer_reading_at", "vehicle_odometer_reading", ["reading_at"]
    )

    # 8. vehicle_fuel_log (FK to vehicle_usage_session — now exists)
    # NOTE: receipt_attachment_id FK to attachment.id will be added in migration 0032
    op.create_table(
        "vehicle_fuel_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "usage_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_usage_session.id"),
            nullable=True,
        ),
        sa.Column(
            "recorded_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.Column("fueled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("liters", sa.Numeric(10, 3), nullable=False),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("odometer_km", sa.Numeric(12, 3), nullable=True),
        sa.Column("station_name", sa.String(150), nullable=True),
        sa.Column(
            "receipt_attachment_id", postgresql.UUID(as_uuid=True), nullable=True
        ),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("liters > 0", name="ck_fuel_liters_positive"),
        sa.CheckConstraint(
            "total_cost IS NULL OR total_cost >= 0", name="ck_fuel_cost_non_negative"
        ),
    )
    op.create_index(
        "idx_vehicle_fuel_log_vehicle_id", "vehicle_fuel_log", ["vehicle_id"]
    )
    op.create_index("idx_vehicle_fuel_log_fueled_at", "vehicle_fuel_log", ["fueled_at"])

    # 9. vehicle_maintenance_type
    op.create_table(
        "vehicle_maintenance_type",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )

    # 10. vehicle_maintenance
    op.create_table(
        "vehicle_maintenance",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "maintenance_type_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_maintenance_type.id"),
            nullable=True,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="planned"),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("scheduled_for", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("odometer_km", sa.Numeric(12, 3), nullable=True),
        sa.Column("supplier_name", sa.String(150), nullable=True),
        sa.Column("cost_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "created_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "completed_at IS NULL OR completed_at >= opened_at",
            name="ck_maintenance_dates",
        ),
    )
    op.create_index(
        "idx_vehicle_maintenance_vehicle_id", "vehicle_maintenance", ["vehicle_id"]
    )
    op.create_index("idx_vehicle_maintenance_status", "vehicle_maintenance", ["status"])
    op.create_index(
        "idx_vehicle_maintenance_scheduled_for",
        "vehicle_maintenance",
        ["scheduled_for"],
    )

    # 11. vehicle_document (FK to attachment.id deferred to 0032)
    op.create_table(
        "vehicle_document",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("document_type", sa.String(50), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("document_number", sa.String(100), nullable=True),
        sa.Column("issued_at", sa.Date, nullable=True),
        sa.Column("expires_at", sa.Date, nullable=True),
        sa.Column("attachment_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("notes", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "idx_vehicle_document_vehicle_id", "vehicle_document", ["vehicle_id"]
    )
    op.create_index(
        "idx_vehicle_document_expires_at", "vehicle_document", ["expires_at"]
    )
    op.create_index(
        "idx_vehicle_document_document_type", "vehicle_document", ["document_type"]
    )


def downgrade() -> None:
    op.drop_table("vehicle_document")
    op.drop_table("vehicle_maintenance")
    op.drop_table("vehicle_maintenance_type")
    op.drop_table("vehicle_fuel_log")
    op.drop_table("vehicle_usage_session")
    op.drop_table("vehicle_odometer_reading")
    op.drop_table("vehicle_assignment")
    op.drop_table("vehicle")
    op.drop_table("operator_profile")
    op.drop_table("team_membership")
    op.drop_table("team")
