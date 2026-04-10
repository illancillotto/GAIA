"""operazioni module — activities, reports, cases, attachments, GPS tables

Revision ID: 20260405_0032
Revises: 20260405_0031
Create Date: 2026-04-05
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260405_0032"
down_revision = "20260405_0031"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. activity_catalog (no FK to new tables)
    op.create_table(
        "activity_catalog",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column(
            "requires_vehicle", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "requires_note", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "sort_order", sa.Integer, nullable=False, server_default=sa.text("0")
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
    )
    op.create_index("idx_activity_catalog_category", "activity_catalog", ["category"])
    op.create_index(
        "idx_activity_catalog_sort_order", "activity_catalog", ["sort_order"]
    )

    # 2. field_report_category (no FK)
    op.create_table(
        "field_report_category",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column(
            "sort_order", sa.Integer, nullable=False, server_default=sa.text("0")
        ),
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

    # 3. field_report_severity (no FK)
    op.create_table(
        "field_report_severity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("code", sa.String(50), unique=True, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("rank_order", sa.Integer, nullable=False),
        sa.Column("color_hex", sa.String(7), nullable=True),
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

    # 4. gps_track_summary (no FK to new tables)
    op.create_table(
        "gps_track_summary",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source_type", sa.String(30), nullable=False),
        sa.Column("provider_name", sa.String(100), nullable=True),
        sa.Column("provider_track_id", sa.String(100), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("start_latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("start_longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("end_latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("end_longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("total_distance_km", sa.Numeric(12, 3), nullable=True),
        sa.Column("total_duration_seconds", sa.Integer, nullable=True),
        sa.Column("raw_payload_json", postgresql.JSONB, nullable=True),
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
        "idx_gps_track_summary_source_type", "gps_track_summary", ["source_type"]
    )
    op.create_index(
        "idx_gps_track_summary_provider_track_id",
        "gps_track_summary",
        ["provider_track_id"],
    )
    op.create_index(
        "idx_gps_track_summary_started_at", "gps_track_summary", ["started_at"]
    )

    # 5. attachment (MUST be before tables that reference it)
    op.create_table(
        "attachment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("storage_path", sa.Text, unique=True, nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("mime_type", sa.String(100), nullable=False),
        sa.Column("extension", sa.String(20), nullable=True),
        sa.Column("attachment_type", sa.String(20), nullable=False),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=False),
        sa.Column("checksum_sha256", sa.String(64), nullable=True),
        sa.Column("width_px", sa.Integer, nullable=True),
        sa.Column("height_px", sa.Integer, nullable=True),
        sa.Column("duration_seconds", sa.Numeric(10, 2), nullable=True),
        sa.Column(
            "was_compressed", sa.Boolean, nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "compression_status",
            sa.String(30),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column(
            "uploaded_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("source_context", sa.String(50), nullable=False),
        sa.Column("source_entity_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("is_deleted", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", postgresql.JSONB, nullable=True),
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
        sa.CheckConstraint("file_size_bytes >= 0", name="ck_attachment_size_positive"),
    )
    op.create_index("idx_attachment_attachment_type", "attachment", ["attachment_type"])
    op.create_index("idx_attachment_created_at", "attachment", ["created_at"])
    op.create_index("idx_attachment_source_context", "attachment", ["source_context"])
    op.create_index(
        "idx_attachment_source_entity_id", "attachment", ["source_entity_id"]
    )
    op.create_index("idx_attachment_is_deleted", "attachment", ["is_deleted"])

    # 6. storage_quota_metric (no FK)
    op.create_table(
        "storage_quota_metric",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("measured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("total_bytes_used", sa.BigInteger, nullable=False),
        sa.Column("quota_bytes", sa.BigInteger, nullable=False),
        sa.Column("percentage_used", sa.Numeric(5, 2), nullable=False),
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

    # 7. storage_quota_alert (FK to storage_quota_metric)
    op.create_table(
        "storage_quota_alert",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("alert_level", sa.String(20), nullable=False),
        sa.Column("threshold_percentage", sa.Numeric(5, 2), nullable=False),
        sa.Column("triggered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metric_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("storage_quota_metric.id"),
            nullable=False,
        ),
        sa.Column("note", sa.Text, nullable=True),
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

    # 8. operator_activity (FK to activity_catalog, team, vehicle, vehicle_usage_session, gps_track_summary, attachment)
    op.create_table(
        "operator_activity",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "activity_catalog_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activity_catalog.id"),
            nullable=False,
        ),
        sa.Column(
            "operator_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team.id"),
            nullable=True,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle.id"),
            nullable=True,
        ),
        sa.Column(
            "vehicle_usage_session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle_usage_session.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_minutes_declared", sa.Integer, nullable=True),
        sa.Column("duration_minutes_calculated", sa.Integer, nullable=True),
        sa.Column("start_latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("start_longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("end_latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("end_longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column(
            "gps_track_summary_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("gps_track_summary.id"),
            nullable=True,
        ),
        sa.Column("text_note", sa.Text, nullable=True),
        sa.Column(
            "audio_note_attachment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("attachment.id"),
            nullable=True,
        ),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "reviewed_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("review_outcome", sa.String(30), nullable=True),
        sa.Column("review_note", sa.Text, nullable=True),
        sa.Column(
            "rectified_from_activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operator_activity.id"),
            nullable=True,
        ),
        sa.Column("offline_client_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
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
            "ended_at IS NULL OR ended_at >= started_at", name="ck_activity_dates"
        ),
        sa.CheckConstraint(
            "duration_minutes_declared IS NULL OR duration_minutes_declared >= 0",
            name="ck_activity_duration_declared",
        ),
        sa.CheckConstraint(
            "duration_minutes_calculated IS NULL OR duration_minutes_calculated >= 0",
            name="ck_activity_duration_calculated",
        ),
    )
    op.create_index(
        "idx_operator_activity_operator_user_id",
        "operator_activity",
        ["operator_user_id"],
    )
    op.create_index("idx_operator_activity_team_id", "operator_activity", ["team_id"])
    op.create_index(
        "idx_operator_activity_vehicle_id", "operator_activity", ["vehicle_id"]
    )
    op.create_index("idx_operator_activity_status", "operator_activity", ["status"])
    op.create_index(
        "idx_operator_activity_started_at", "operator_activity", ["started_at"]
    )
    op.create_index(
        "idx_operator_activity_activity_catalog_id",
        "operator_activity",
        ["activity_catalog_id"],
    )
    op.create_index(
        "idx_operator_activity_offline_client_uuid",
        "operator_activity",
        ["offline_client_uuid"],
    )

    # 9. operator_activity_event (FK to operator_activity)
    op.create_table(
        "operator_activity_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operator_activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operator_activity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("payload_json", postgresql.JSONB, nullable=True),
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
        "idx_operator_activity_event_activity_id",
        "operator_activity_event",
        ["operator_activity_id"],
    )
    op.create_index(
        "idx_operator_activity_event_event_type",
        "operator_activity_event",
        ["event_type"],
    )
    op.create_index(
        "idx_operator_activity_event_event_at", "operator_activity_event", ["event_at"]
    )

    # 10. operator_activity_attachment (FK to operator_activity, attachment)
    op.create_table(
        "operator_activity_attachment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operator_activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operator_activity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "attachment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("attachment.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
    op.create_unique_constraint(
        "uq_activity_attachment",
        "operator_activity_attachment",
        ["operator_activity_id", "attachment_id"],
    )

    # 11. activity_approval (FK to operator_activity)
    op.create_table(
        "activity_approval",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "operator_activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operator_activity.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "reviewer_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.Column("decision", sa.String(30), nullable=False),
        sa.Column("decision_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("payload_json", postgresql.JSONB, nullable=True),
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
        "idx_activity_approval_operator_activity_id",
        "activity_approval",
        ["operator_activity_id"],
    )
    op.create_index(
        "idx_activity_approval_reviewer_user_id",
        "activity_approval",
        ["reviewer_user_id"],
    )
    op.create_index(
        "idx_activity_approval_decision_at", "activity_approval", ["decision_at"]
    )

    # 12. field_report (FK to application_users, team, vehicle, operator_activity, field_report_category, field_report_severity)
    op.create_table(
        "field_report",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("report_number", sa.String(50), unique=True, nullable=False),
        sa.Column(
            "reporter_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=False,
        ),
        sa.Column(
            "team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team.id"),
            nullable=True,
        ),
        sa.Column(
            "vehicle_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("vehicle.id"),
            nullable=True,
        ),
        sa.Column(
            "operator_activity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("operator_activity.id"),
            nullable=True,
        ),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_report_category.id"),
            nullable=False,
        ),
        sa.Column(
            "severity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_report_severity.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("latitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("longitude", sa.Numeric(10, 7), nullable=True),
        sa.Column("gps_accuracy_meters", sa.Numeric(10, 2), nullable=True),
        sa.Column("gps_source", sa.String(30), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="submitted"),
        sa.Column("offline_client_uuid", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("client_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("server_received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "internal_case_id",
            postgresql.UUID(as_uuid=True),
            unique=True,
            nullable=True,
        ),
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
    op.create_index(
        "idx_field_report_reporter_user_id", "field_report", ["reporter_user_id"]
    )
    op.create_index("idx_field_report_category_id", "field_report", ["category_id"])
    op.create_index("idx_field_report_severity_id", "field_report", ["severity_id"])
    op.create_index("idx_field_report_vehicle_id", "field_report", ["vehicle_id"])
    op.create_index(
        "idx_field_report_operator_activity_id",
        "field_report",
        ["operator_activity_id"],
    )
    op.create_index("idx_field_report_created_at", "field_report", ["created_at"])
    op.create_index(
        "idx_field_report_offline_client_uuid", "field_report", ["offline_client_uuid"]
    )

    # 13. field_report_attachment (FK to field_report, attachment)
    op.create_table(
        "field_report_attachment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "field_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_report.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "attachment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("attachment.id", ondelete="CASCADE"),
            nullable=False,
        ),
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
    op.create_unique_constraint(
        "uq_report_attachment",
        "field_report_attachment",
        ["field_report_id", "attachment_id"],
    )

    # 14. internal_case (FK to field_report, field_report_category, field_report_severity, application_users, team)
    op.create_table(
        "internal_case",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("case_number", sa.String(50), unique=True, nullable=False),
        sa.Column(
            "source_report_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_report.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column(
            "category_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_report_category.id"),
            nullable=True,
        ),
        sa.Column(
            "severity_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("field_report_severity.id"),
            nullable=True,
        ),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column(
            "assigned_to_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column(
            "assigned_team_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("team.id"),
            nullable=True,
        ),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.Text, nullable=True),
        sa.Column(
            "closed_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("priority_rank", sa.Integer, nullable=True),
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
    op.create_index("idx_internal_case_status", "internal_case", ["status"])
    op.create_index(
        "idx_internal_case_assigned_to_user_id",
        "internal_case",
        ["assigned_to_user_id"],
    )
    op.create_index(
        "idx_internal_case_assigned_team_id", "internal_case", ["assigned_team_id"]
    )
    op.create_index("idx_internal_case_created_at", "internal_case", ["created_at"])
    op.create_index("idx_internal_case_severity_id", "internal_case", ["severity_id"])

    # 15. internal_case_event (FK to internal_case)
    op.create_table(
        "internal_case_event",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "internal_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internal_case.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(50), nullable=False),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column("payload_json", postgresql.JSONB, nullable=True),
        sa.Column("note", sa.Text, nullable=True),
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
        "idx_internal_case_event_case_id", "internal_case_event", ["internal_case_id"]
    )
    op.create_index(
        "idx_internal_case_event_event_type", "internal_case_event", ["event_type"]
    )
    op.create_index(
        "idx_internal_case_event_event_at", "internal_case_event", ["event_at"]
    )

    # 16. internal_case_attachment (FK to internal_case, attachment)
    op.create_table(
        "internal_case_attachment",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "internal_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internal_case.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "attachment_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("attachment.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "uploaded_by_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
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

    # 17. internal_case_assignment_history (FK to internal_case, application_users, team)
    op.create_table(
        "internal_case_assignment_history",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "internal_case_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("internal_case.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "assigned_to_user_id",
            sa.Integer,
            sa.ForeignKey("application_users.id"),
            nullable=True,
        ),
        sa.Column(
            "assigned_team_id",
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
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("unassigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
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

    # 18. Add FK constraints to 0031 tables that reference attachment
    op.create_foreign_key(
        "fk_vehicle_fuel_log_receipt_attachment",
        "vehicle_fuel_log",
        "attachment",
        ["receipt_attachment_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_vehicle_document_attachment",
        "vehicle_document",
        "attachment",
        ["attachment_id"],
        ["id"],
    )


def downgrade() -> None:
    # Drop FK constraints added to 0031 tables
    op.drop_constraint(
        "fk_vehicle_document_attachment", "vehicle_document", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_vehicle_fuel_log_receipt_attachment", "vehicle_fuel_log", type_="foreignkey"
    )

    op.drop_table("internal_case_assignment_history")
    op.drop_table("internal_case_attachment")
    op.drop_table("internal_case_event")
    op.drop_table("internal_case")
    op.drop_table("field_report_attachment")
    op.drop_table("field_report")
    op.drop_table("activity_approval")
    op.drop_table("operator_activity_attachment")
    op.drop_table("operator_activity_event")
    op.drop_table("operator_activity")
    op.drop_table("storage_quota_alert")
    op.drop_table("storage_quota_metric")
    op.drop_table("attachment")
    op.drop_table("gps_track_summary")
    op.drop_table("field_report_severity")
    op.drop_table("field_report_category")
    op.drop_table("activity_catalog")
