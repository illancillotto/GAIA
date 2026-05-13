"""catasto: add AdE WFS particelle staging

Revision ID: 20260513_0076
Revises: 20260512_0075
Create Date: 2026-05-13 10:40:00.000000
"""

from __future__ import annotations

from alembic import op
import geoalchemy2
import sqlalchemy as sa


revision = "20260513_0076"
down_revision = "20260512_0075"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cat_ade_sync_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="processing", nullable=False),
        sa.Column("request_bbox_json", sa.JSON(), nullable=False),
        sa.Column("max_tile_km2", sa.Numeric(10, 3), nullable=True),
        sa.Column("max_tiles", sa.Integer(), nullable=True),
        sa.Column("count_per_page", sa.Integer(), nullable=True),
        sa.Column("max_pages_per_tile", sa.Integer(), nullable=True),
        sa.Column("tiles", sa.Integer(), server_default="0", nullable=False),
        sa.Column("features", sa.Integer(), server_default="0", nullable=False),
        sa.Column("upserted", sa.Integer(), server_default="0", nullable=False),
        sa.Column("with_geometry", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["application_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_cat_ade_sync_runs_status", "cat_ade_sync_runs", ["status"])
    op.create_table(
        "cat_ade_particelle",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("source_run_id", sa.Uuid(), nullable=True),
        sa.Column("inspire_id_local_id", sa.String(length=120), nullable=True),
        sa.Column("inspire_id_namespace", sa.String(length=80), nullable=True),
        sa.Column("national_cadastral_reference", sa.String(length=80), nullable=False),
        sa.Column("administrative_unit", sa.String(length=4), nullable=True),
        sa.Column("codice_catastale", sa.String(length=4), nullable=True),
        sa.Column("sezione_catastale", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("foglio_raw", sa.String(length=10), nullable=True),
        sa.Column("allegato", sa.String(length=5), nullable=True),
        sa.Column("sviluppo", sa.String(length=5), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("particella_raw", sa.String(length=20), nullable=True),
        sa.Column("label", sa.String(length=80), nullable=True),
        sa.Column("geometry", geoalchemy2.Geometry(geometry_type="MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("source_crs", sa.String(length=32), server_default="EPSG:6706", nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("fetched_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["source_run_id"], ["cat_ade_sync_runs.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("national_cadastral_reference", name="uq_cat_ade_particelle_national_ref"),
    )
    op.create_index("ix_cat_ade_particelle_source_run_id", "cat_ade_particelle", ["source_run_id"])
    op.create_index("ix_cat_ade_particelle_inspire_id_local_id", "cat_ade_particelle", ["inspire_id_local_id"])
    op.create_index("ix_cat_ade_particelle_national_cadastral_reference", "cat_ade_particelle", ["national_cadastral_reference"])
    op.create_index("ix_cat_ade_particelle_administrative_unit", "cat_ade_particelle", ["administrative_unit"])
    op.create_index("ix_cat_ade_particelle_codice_catastale", "cat_ade_particelle", ["codice_catastale"])
    op.create_index("ix_cat_ade_particelle_foglio", "cat_ade_particelle", ["foglio"])
    op.create_index("ix_cat_ade_particelle_particella", "cat_ade_particelle", ["particella"])
    op.create_index("idx_cat_ade_particelle_geom", "cat_ade_particelle", ["geometry"], postgresql_using="gist")


def downgrade() -> None:
    op.drop_index("idx_cat_ade_particelle_geom", table_name="cat_ade_particelle", postgresql_using="gist")
    op.drop_index("ix_cat_ade_particelle_particella", table_name="cat_ade_particelle")
    op.drop_index("ix_cat_ade_particelle_foglio", table_name="cat_ade_particelle")
    op.drop_index("ix_cat_ade_particelle_codice_catastale", table_name="cat_ade_particelle")
    op.drop_index("ix_cat_ade_particelle_administrative_unit", table_name="cat_ade_particelle")
    op.drop_index("ix_cat_ade_particelle_national_cadastral_reference", table_name="cat_ade_particelle")
    op.drop_index("ix_cat_ade_particelle_inspire_id_local_id", table_name="cat_ade_particelle")
    op.drop_index("ix_cat_ade_particelle_source_run_id", table_name="cat_ade_particelle")
    op.drop_table("cat_ade_particelle")
    op.drop_index("ix_cat_ade_sync_runs_status", table_name="cat_ade_sync_runs")
    op.drop_table("cat_ade_sync_runs")
