"""add governed GIS platform MVP

Revision ID: 20260713_0900
Revises: 20260708_1400, 20260708_1700
Create Date: 2026-07-13 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260713_0900"
down_revision: str | Sequence[str] | None = ("20260708_1400", "20260708_1700")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gis_layers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("workspace", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("domain_module", sa.String(length=80), nullable=True),
        sa.Column("source_type", sa.String(length=32), nullable=False),
        sa.Column("official_source", sa.String(length=32), nullable=False),
        sa.Column("postgis_schema", sa.String(length=80), nullable=True),
        sa.Column("postgis_table", sa.String(length=160), nullable=True),
        sa.Column("geometry_column", sa.String(length=80), nullable=True),
        sa.Column("geometry_type", sa.String(length=64), nullable=True),
        sa.Column("srid", sa.Integer(), nullable=True),
        sa.Column("feature_id_column", sa.String(length=80), nullable=True),
        sa.Column("martin_layer_id", sa.String(length=160), nullable=True),
        sa.Column("ogc_service_url", sa.Text(), nullable=True),
        sa.Column("qgis_project_path", sa.Text(), nullable=True),
        sa.Column("nas_export_root", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace", "name", name="uq_gis_layers_workspace_name"),
    )
    op.create_index(op.f("ix_gis_layers_domain_module"), "gis_layers", ["domain_module"], unique=False)
    op.create_index(op.f("ix_gis_layers_is_active"), "gis_layers", ["is_active"], unique=False)
    op.create_index(op.f("ix_gis_layers_martin_layer_id"), "gis_layers", ["martin_layer_id"], unique=False)
    op.create_index(op.f("ix_gis_layers_name"), "gis_layers", ["name"], unique=False)
    op.create_index(op.f("ix_gis_layers_source_type"), "gis_layers", ["source_type"], unique=False)
    op.create_index(op.f("ix_gis_layers_workspace"), "gis_layers", ["workspace"], unique=False)

    op.create_table(
        "gis_layer_permissions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("layer_id", sa.Uuid(), nullable=False),
        sa.Column("principal_type", sa.String(length=32), nullable=False),
        sa.Column("principal_key", sa.String(length=120), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("can_view", sa.Boolean(), nullable=False),
        sa.Column("can_annotate", sa.Boolean(), nullable=False),
        sa.Column("can_edit", sa.Boolean(), nullable=False),
        sa.Column("can_approve", sa.Boolean(), nullable=False),
        sa.Column("can_manage", sa.Boolean(), nullable=False),
        sa.Column("granted_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["granted_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["layer_id"], ["gis_layers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("layer_id", "principal_type", "principal_key", name="uq_gis_layer_permissions_principal"),
    )
    op.create_index(op.f("ix_gis_layer_permissions_layer_id"), "gis_layer_permissions", ["layer_id"], unique=False)
    op.create_index(op.f("ix_gis_layer_permissions_principal_key"), "gis_layer_permissions", ["principal_key"], unique=False)
    op.create_index(op.f("ix_gis_layer_permissions_principal_type"), "gis_layer_permissions", ["principal_type"], unique=False)
    op.create_index(op.f("ix_gis_layer_permissions_user_id"), "gis_layer_permissions", ["user_id"], unique=False)

    op.create_table(
        "gis_annotations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("layer_id", sa.Uuid(), nullable=False),
        sa.Column("feature_id", sa.String(length=255), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("geometry_json", sa.JSON(), nullable=True),
        sa.Column("attachment_refs_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["layer_id"], ["gis_layers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gis_annotations_created_by_user_id"), "gis_annotations", ["created_by_user_id"], unique=False)
    op.create_index(op.f("ix_gis_annotations_feature_id"), "gis_annotations", ["feature_id"], unique=False)
    op.create_index(op.f("ix_gis_annotations_layer_id"), "gis_annotations", ["layer_id"], unique=False)
    op.create_index(op.f("ix_gis_annotations_status"), "gis_annotations", ["status"], unique=False)

    op.create_table(
        "gis_change_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("layer_id", sa.Uuid(), nullable=False),
        sa.Column("feature_id", sa.String(length=255), nullable=True),
        sa.Column("change_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("justification", sa.Text(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("reviewed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["layer_id"], ["gis_layers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["reviewed_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gis_change_requests_change_type"), "gis_change_requests", ["change_type"], unique=False)
    op.create_index(op.f("ix_gis_change_requests_feature_id"), "gis_change_requests", ["feature_id"], unique=False)
    op.create_index(op.f("ix_gis_change_requests_layer_id"), "gis_change_requests", ["layer_id"], unique=False)
    op.create_index(op.f("ix_gis_change_requests_requested_by_user_id"), "gis_change_requests", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_gis_change_requests_status"), "gis_change_requests", ["status"], unique=False)

    op.create_table(
        "gis_layer_exports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("layer_id", sa.Uuid(), nullable=False),
        sa.Column("version_label", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("nas_path", sa.Text(), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["layer_id"], ["gis_layers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gis_layer_exports_layer_id"), "gis_layer_exports", ["layer_id"], unique=False)
    op.create_index(op.f("ix_gis_layer_exports_requested_by_user_id"), "gis_layer_exports", ["requested_by_user_id"], unique=False)
    op.create_index(op.f("ix_gis_layer_exports_status"), "gis_layer_exports", ["status"], unique=False)
    op.create_index(op.f("ix_gis_layer_exports_version_label"), "gis_layer_exports", ["version_label"], unique=False)

    op.create_table(
        "gis_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("layer_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("target_type", sa.String(length=80), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["layer_id"], ["gis_layers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gis_audit_logs_actor_user_id"), "gis_audit_logs", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_gis_audit_logs_event_type"), "gis_audit_logs", ["event_type"], unique=False)
    op.create_index(op.f("ix_gis_audit_logs_layer_id"), "gis_audit_logs", ["layer_id"], unique=False)
    op.create_index(op.f("ix_gis_audit_logs_target_id"), "gis_audit_logs", ["target_id"], unique=False)


def downgrade() -> None:
    op.drop_table("gis_audit_logs")
    op.drop_table("gis_layer_exports")
    op.drop_table("gis_change_requests")
    op.drop_table("gis_annotations")
    op.drop_table("gis_layer_permissions")
    op.drop_table("gis_layers")
