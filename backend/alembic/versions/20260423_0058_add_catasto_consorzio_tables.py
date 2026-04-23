"""add catasto consorzio support tables

Revision ID: 20260423_0058
Revises: 20260423_0057
Create Date: 2026-04-23

"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision = "20260423_0058"
down_revision: Union[str, None] = "20260423_0057"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cat_consorzio_units",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("particella_id", sa.Uuid(), nullable=True),
        sa.Column("comune_id", sa.Uuid(), nullable=True),
        sa.Column("cod_comune_capacitas", sa.Integer(), nullable=True),
        sa.Column("sezione_catastale", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("subalterno", sa.String(length=10), nullable=True),
        sa.Column("descrizione", sa.String(length=255), nullable=True),
        sa.Column("source_first_seen", sa.Date(), nullable=True),
        sa.Column("source_last_seen", sa.Date(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["comune_id"], ["cat_comuni.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["particella_id"], ["cat_particelle.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cat_consorzio_units_cod_comune_capacitas"), "cat_consorzio_units", ["cod_comune_capacitas"])
    op.create_index(op.f("ix_cat_consorzio_units_comune_id"), "cat_consorzio_units", ["comune_id"])
    op.create_index(op.f("ix_cat_consorzio_units_foglio"), "cat_consorzio_units", ["foglio"])
    op.create_index(op.f("ix_cat_consorzio_units_is_active"), "cat_consorzio_units", ["is_active"])
    op.create_index(op.f("ix_cat_consorzio_units_particella"), "cat_consorzio_units", ["particella"])
    op.create_index(op.f("ix_cat_consorzio_units_particella_id"), "cat_consorzio_units", ["particella_id"])

    op.create_table(
        "cat_consorzio_unit_segments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("label", sa.String(length=100), nullable=True),
        sa.Column("segment_type", sa.String(length=40), nullable=False),
        sa.Column("surface_declared_mq", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("surface_irrigable_mq", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("riordino_code", sa.String(length=50), nullable=True),
        sa.Column("riordino_maglia", sa.String(length=20), nullable=True),
        sa.Column("riordino_lotto", sa.String(length=20), nullable=True),
        sa.Column("current_status", sa.String(length=40), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["cat_consorzio_units.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cat_consorzio_unit_segments_is_current"), "cat_consorzio_unit_segments", ["is_current"])
    op.create_index(op.f("ix_cat_consorzio_unit_segments_riordino_code"), "cat_consorzio_unit_segments", ["riordino_code"])
    op.create_index(op.f("ix_cat_consorzio_unit_segments_segment_type"), "cat_consorzio_unit_segments", ["segment_type"])
    op.create_index(op.f("ix_cat_consorzio_unit_segments_unit_id"), "cat_consorzio_unit_segments", ["unit_id"])

    op.create_table(
        "cat_consorzio_occupancies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=False),
        sa.Column("segment_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("utenza_id", sa.Uuid(), nullable=True),
        sa.Column("cco", sa.String(length=20), nullable=True),
        sa.Column("fra", sa.String(length=20), nullable=True),
        sa.Column("ccs", sa.String(length=20), nullable=True),
        sa.Column("pvc", sa.String(length=10), nullable=True),
        sa.Column("com", sa.String(length=10), nullable=True),
        sa.Column("source_type", sa.String(length=40), nullable=False),
        sa.Column("relationship_type", sa.String(length=40), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=True),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("confidence", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["segment_id"], ["cat_consorzio_unit_segments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["cat_consorzio_units.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["utenza_id"], ["cat_utenze_irrigue.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cat_consorzio_occupancies_cco"), "cat_consorzio_occupancies", ["cco"])
    op.create_index(op.f("ix_cat_consorzio_occupancies_is_current"), "cat_consorzio_occupancies", ["is_current"])
    op.create_index(
        op.f("ix_cat_consorzio_occupancies_relationship_type"),
        "cat_consorzio_occupancies",
        ["relationship_type"],
    )
    op.create_index(op.f("ix_cat_consorzio_occupancies_segment_id"), "cat_consorzio_occupancies", ["segment_id"])
    op.create_index(op.f("ix_cat_consorzio_occupancies_source_type"), "cat_consorzio_occupancies", ["source_type"])
    op.create_index(op.f("ix_cat_consorzio_occupancies_subject_id"), "cat_consorzio_occupancies", ["subject_id"])
    op.create_index(op.f("ix_cat_consorzio_occupancies_unit_id"), "cat_consorzio_occupancies", ["unit_id"])
    op.create_index(op.f("ix_cat_consorzio_occupancies_utenza_id"), "cat_consorzio_occupancies", ["utenza_id"])

    op.create_table(
        "cat_capacitas_terreni_rows",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("unit_id", sa.Uuid(), nullable=True),
        sa.Column("search_key", sa.String(length=255), nullable=True),
        sa.Column("external_row_id", sa.String(length=64), nullable=True),
        sa.Column("cco", sa.String(length=20), nullable=True),
        sa.Column("fra", sa.String(length=20), nullable=True),
        sa.Column("ccs", sa.String(length=20), nullable=True),
        sa.Column("pvc", sa.String(length=10), nullable=True),
        sa.Column("com", sa.String(length=10), nullable=True),
        sa.Column("belfiore", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("sub", sa.String(length=10), nullable=True),
        sa.Column("anno", sa.Integer(), nullable=True),
        sa.Column("voltura", sa.String(length=20), nullable=True),
        sa.Column("opcode", sa.String(length=20), nullable=True),
        sa.Column("data_reg", sa.String(length=20), nullable=True),
        sa.Column("superficie_mq", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("bac_descr", sa.String(length=255), nullable=True),
        sa.Column("row_visual_state", sa.String(length=40), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["unit_id"], ["cat_consorzio_units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cat_capacitas_terreni_rows_anno"), "cat_capacitas_terreni_rows", ["anno"])
    op.create_index(op.f("ix_cat_capacitas_terreni_rows_cco"), "cat_capacitas_terreni_rows", ["cco"])
    op.create_index(
        op.f("ix_cat_capacitas_terreni_rows_external_row_id"),
        "cat_capacitas_terreni_rows",
        ["external_row_id"],
    )
    op.create_index(op.f("ix_cat_capacitas_terreni_rows_foglio"), "cat_capacitas_terreni_rows", ["foglio"])
    op.create_index(op.f("ix_cat_capacitas_terreni_rows_particella"), "cat_capacitas_terreni_rows", ["particella"])
    op.create_index(
        op.f("ix_cat_capacitas_terreni_rows_row_visual_state"),
        "cat_capacitas_terreni_rows",
        ["row_visual_state"],
    )
    op.create_index(op.f("ix_cat_capacitas_terreni_rows_search_key"), "cat_capacitas_terreni_rows", ["search_key"])
    op.create_index(op.f("ix_cat_capacitas_terreni_rows_unit_id"), "cat_capacitas_terreni_rows", ["unit_id"])

    op.create_table(
        "cat_capacitas_certificati",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("cco", sa.String(length=20), nullable=False),
        sa.Column("fra", sa.String(length=20), nullable=True),
        sa.Column("ccs", sa.String(length=20), nullable=True),
        sa.Column("pvc", sa.String(length=10), nullable=True),
        sa.Column("com", sa.String(length=10), nullable=True),
        sa.Column("partita_code", sa.String(length=50), nullable=True),
        sa.Column("utenza_code", sa.String(length=50), nullable=True),
        sa.Column("utenza_status", sa.String(length=100), nullable=True),
        sa.Column("ruolo_status", sa.String(length=100), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("parsed_json", sa.JSON(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cco", "fra", "ccs", "pvc", "com", "collected_at", name="uq_cat_cap_cert_snapshot"),
    )
    op.create_index(op.f("ix_cat_capacitas_certificati_cco"), "cat_capacitas_certificati", ["cco"])

    op.create_table(
        "cat_capacitas_terreno_details",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("terreno_row_id", sa.Uuid(), nullable=True),
        sa.Column("external_row_id", sa.String(length=64), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("sub", sa.String(length=10), nullable=True),
        sa.Column("riordino_code", sa.String(length=50), nullable=True),
        sa.Column("riordino_maglia", sa.String(length=20), nullable=True),
        sa.Column("riordino_lotto", sa.String(length=20), nullable=True),
        sa.Column("irridist", sa.String(length=50), nullable=True),
        sa.Column("raw_html", sa.Text(), nullable=True),
        sa.Column("parsed_json", sa.JSON(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["terreno_row_id"], ["cat_capacitas_terreni_rows.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cat_capacitas_terreno_details_external_row_id"),
        "cat_capacitas_terreno_details",
        ["external_row_id"],
    )
    op.create_index(
        op.f("ix_cat_capacitas_terreno_details_riordino_code"),
        "cat_capacitas_terreno_details",
        ["riordino_code"],
    )
    op.create_index(
        op.f("ix_cat_capacitas_terreno_details_terreno_row_id"),
        "cat_capacitas_terreno_details",
        ["terreno_row_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cat_capacitas_terreno_details_terreno_row_id"), table_name="cat_capacitas_terreno_details")
    op.drop_index(op.f("ix_cat_capacitas_terreno_details_riordino_code"), table_name="cat_capacitas_terreno_details")
    op.drop_index(op.f("ix_cat_capacitas_terreno_details_external_row_id"), table_name="cat_capacitas_terreno_details")
    op.drop_table("cat_capacitas_terreno_details")

    op.drop_index(op.f("ix_cat_capacitas_certificati_cco"), table_name="cat_capacitas_certificati")
    op.drop_table("cat_capacitas_certificati")

    op.drop_index(op.f("ix_cat_capacitas_terreni_rows_unit_id"), table_name="cat_capacitas_terreni_rows")
    op.drop_index(op.f("ix_cat_capacitas_terreni_rows_search_key"), table_name="cat_capacitas_terreni_rows")
    op.drop_index(op.f("ix_cat_capacitas_terreni_rows_row_visual_state"), table_name="cat_capacitas_terreni_rows")
    op.drop_index(op.f("ix_cat_capacitas_terreni_rows_particella"), table_name="cat_capacitas_terreni_rows")
    op.drop_index(op.f("ix_cat_capacitas_terreni_rows_foglio"), table_name="cat_capacitas_terreni_rows")
    op.drop_index(op.f("ix_cat_capacitas_terreni_rows_external_row_id"), table_name="cat_capacitas_terreni_rows")
    op.drop_index(op.f("ix_cat_capacitas_terreni_rows_cco"), table_name="cat_capacitas_terreni_rows")
    op.drop_index(op.f("ix_cat_capacitas_terreni_rows_anno"), table_name="cat_capacitas_terreni_rows")
    op.drop_table("cat_capacitas_terreni_rows")

    op.drop_index(op.f("ix_cat_consorzio_occupancies_utenza_id"), table_name="cat_consorzio_occupancies")
    op.drop_index(op.f("ix_cat_consorzio_occupancies_unit_id"), table_name="cat_consorzio_occupancies")
    op.drop_index(op.f("ix_cat_consorzio_occupancies_subject_id"), table_name="cat_consorzio_occupancies")
    op.drop_index(op.f("ix_cat_consorzio_occupancies_source_type"), table_name="cat_consorzio_occupancies")
    op.drop_index(op.f("ix_cat_consorzio_occupancies_segment_id"), table_name="cat_consorzio_occupancies")
    op.drop_index(op.f("ix_cat_consorzio_occupancies_relationship_type"), table_name="cat_consorzio_occupancies")
    op.drop_index(op.f("ix_cat_consorzio_occupancies_is_current"), table_name="cat_consorzio_occupancies")
    op.drop_index(op.f("ix_cat_consorzio_occupancies_cco"), table_name="cat_consorzio_occupancies")
    op.drop_table("cat_consorzio_occupancies")

    op.drop_index(op.f("ix_cat_consorzio_unit_segments_unit_id"), table_name="cat_consorzio_unit_segments")
    op.drop_index(op.f("ix_cat_consorzio_unit_segments_segment_type"), table_name="cat_consorzio_unit_segments")
    op.drop_index(op.f("ix_cat_consorzio_unit_segments_riordino_code"), table_name="cat_consorzio_unit_segments")
    op.drop_index(op.f("ix_cat_consorzio_unit_segments_is_current"), table_name="cat_consorzio_unit_segments")
    op.drop_table("cat_consorzio_unit_segments")

    op.drop_index(op.f("ix_cat_consorzio_units_particella_id"), table_name="cat_consorzio_units")
    op.drop_index(op.f("ix_cat_consorzio_units_particella"), table_name="cat_consorzio_units")
    op.drop_index(op.f("ix_cat_consorzio_units_is_active"), table_name="cat_consorzio_units")
    op.drop_index(op.f("ix_cat_consorzio_units_foglio"), table_name="cat_consorzio_units")
    op.drop_index(op.f("ix_cat_consorzio_units_comune_id"), table_name="cat_consorzio_units")
    op.drop_index(op.f("ix_cat_consorzio_units_cod_comune_capacitas"), table_name="cat_consorzio_units")
    op.drop_table("cat_consorzio_units")
