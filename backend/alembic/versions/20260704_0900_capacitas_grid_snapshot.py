"""add capacitas grid snapshot tables

Revision ID: 20260704_0900
Revises: 20260703_1900
Create Date: 2026-07-04 09:00:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260704_0900"
down_revision = "20260703_1900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cat_capacitas_grid_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_year", sa.Integer(), nullable=False),
        sa.Column("source_file", sa.String(length=1024), nullable=False),
        sa.Column("file_hash", sa.String(length=64), nullable=False),
        sa.Column("rows_total", sa.Integer(), nullable=False),
        sa.Column("rows_imported", sa.Integer(), nullable=False),
        sa.Column("counters_json", sa.JSON(), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_year", "file_hash", name="uq_cat_capacitas_grid_snapshots_year_hash"),
    )
    op.create_index(op.f("ix_cat_capacitas_grid_snapshots_file_hash"), "cat_capacitas_grid_snapshots", ["file_hash"])
    op.create_index(op.f("ix_cat_capacitas_grid_snapshots_snapshot_year"), "cat_capacitas_grid_snapshots", ["snapshot_year"])

    op.create_table(
        "cat_capacitas_grid_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=True),
        sa.Column("occupancy_id", sa.Uuid(), nullable=True),
        sa.Column("source_codice_catastale", sa.String(length=4), nullable=True),
        sa.Column("source_cod_comune_capacitas", sa.Integer(), nullable=True),
        sa.Column("source_comune_label", sa.String(length=100), nullable=True),
        sa.Column("cco", sa.String(length=20), nullable=True),
        sa.Column("fra", sa.String(length=20), nullable=True),
        sa.Column("ccs", sa.String(length=20), nullable=True),
        sa.Column("pvc", sa.String(length=10), nullable=True),
        sa.Column("sezione_catastale", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("subalterno", sa.String(length=10), nullable=True),
        sa.Column("sup_catastale_mq", sa.Numeric(12, 2), nullable=True),
        sa.Column("sup_irrigata_mq", sa.Numeric(12, 2), nullable=True),
        sa.Column("coltura", sa.String(length=100), nullable=True),
        sa.Column("intestatario", sa.String(length=500), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=True),
        sa.Column("manutenzione", sa.Integer(), nullable=True),
        sa.Column("domanda", sa.Integer(), nullable=True),
        sa.Column("numdomanda", sa.String(length=50), nullable=True),
        sa.Column("stato", sa.String(length=100), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("autorinnovo", sa.Integer(), nullable=True),
        sa.Column("classification", sa.String(length=60), nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["occupancy_id"], ["cat_consorzio_occupancies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["snapshot_id"], ["cat_capacitas_grid_snapshots.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["unit_id"], ["cat_consorzio_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("snapshot_id", "row_number", name="uq_cat_capacitas_grid_rows_snapshot_row"),
    )
    op.create_index(op.f("ix_cat_capacitas_grid_rows_snapshot_id"), "cat_capacitas_grid_rows", ["snapshot_id"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_unit_id"), "cat_capacitas_grid_rows", ["unit_id"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_occupancy_id"), "cat_capacitas_grid_rows", ["occupancy_id"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_source_codice_catastale"), "cat_capacitas_grid_rows", ["source_codice_catastale"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_source_cod_comune_capacitas"), "cat_capacitas_grid_rows", ["source_cod_comune_capacitas"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_cco"), "cat_capacitas_grid_rows", ["cco"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_foglio"), "cat_capacitas_grid_rows", ["foglio"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_particella"), "cat_capacitas_grid_rows", ["particella"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_codice_fiscale"), "cat_capacitas_grid_rows", ["codice_fiscale"])
    op.create_index(op.f("ix_cat_capacitas_grid_rows_classification"), "cat_capacitas_grid_rows", ["classification"])


def downgrade() -> None:
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_classification"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_codice_fiscale"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_particella"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_foglio"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_cco"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_source_cod_comune_capacitas"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_source_codice_catastale"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_occupancy_id"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_unit_id"), table_name="cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_rows_snapshot_id"), table_name="cat_capacitas_grid_rows")
    op.drop_table("cat_capacitas_grid_rows")
    op.drop_index(op.f("ix_cat_capacitas_grid_snapshots_snapshot_year"), table_name="cat_capacitas_grid_snapshots")
    op.drop_index(op.f("ix_cat_capacitas_grid_snapshots_file_hash"), table_name="cat_capacitas_grid_snapshots")
    op.drop_table("cat_capacitas_grid_snapshots")
