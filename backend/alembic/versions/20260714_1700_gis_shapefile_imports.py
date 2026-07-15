"""add GIS shapefile import staging records

Revision ID: 20260714_1700
Revises: 20260714_1100
Create Date: 2026-07-14 17:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260714_1700"
down_revision: str | Sequence[str] | None = "20260714_1100"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gis_shapefile_imports",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("workspace", sa.String(length=80), nullable=False),
        sa.Column("domain_module", sa.String(length=80), nullable=True),
        sa.Column("target_layer_name", sa.String(length=120), nullable=False),
        sa.Column("target_layer_title", sa.String(length=255), nullable=False),
        sa.Column("official_source", sa.String(length=32), nullable=False),
        sa.Column("source_srid", sa.Integer(), nullable=False),
        sa.Column("encoding", sa.String(length=40), nullable=False),
        sa.Column("staging_schema", sa.String(length=80), nullable=True),
        sa.Column("staging_table", sa.String(length=160), nullable=False),
        sa.Column("feature_count", sa.Integer(), nullable=False),
        sa.Column("geometry_type", sa.String(length=64), nullable=True),
        sa.Column("bbox_json", sa.JSON(), nullable=True),
        sa.Column("field_schema_json", sa.JSON(), nullable=True),
        sa.Column("validation_report_json", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("uploaded_by_user_id", sa.Integer(), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejected_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["uploaded_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_gis_shapefile_imports_domain_module"), "gis_shapefile_imports", ["domain_module"], unique=False)
    op.create_index(op.f("ix_gis_shapefile_imports_staging_table"), "gis_shapefile_imports", ["staging_table"], unique=False)
    op.create_index(op.f("ix_gis_shapefile_imports_status"), "gis_shapefile_imports", ["status"], unique=False)
    op.create_index(op.f("ix_gis_shapefile_imports_target_layer_name"), "gis_shapefile_imports", ["target_layer_name"], unique=False)
    op.create_index(op.f("ix_gis_shapefile_imports_uploaded_by_user_id"), "gis_shapefile_imports", ["uploaded_by_user_id"], unique=False)
    op.create_index(op.f("ix_gis_shapefile_imports_workspace"), "gis_shapefile_imports", ["workspace"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_gis_shapefile_imports_workspace"), table_name="gis_shapefile_imports")
    op.drop_index(op.f("ix_gis_shapefile_imports_uploaded_by_user_id"), table_name="gis_shapefile_imports")
    op.drop_index(op.f("ix_gis_shapefile_imports_target_layer_name"), table_name="gis_shapefile_imports")
    op.drop_index(op.f("ix_gis_shapefile_imports_status"), table_name="gis_shapefile_imports")
    op.drop_index(op.f("ix_gis_shapefile_imports_staging_table"), table_name="gis_shapefile_imports")
    op.drop_index(op.f("ix_gis_shapefile_imports_domain_module"), table_name="gis_shapefile_imports")
    op.drop_table("gis_shapefile_imports")
