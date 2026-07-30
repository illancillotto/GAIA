"""catasto domande irrigue

Revision ID: 20260730_0900
Revises: 20260729_0900
Create Date: 2026-07-30
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260730_0900"
down_revision = "20260729_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capacitas_domande_irrigue_sync_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("mode", sa.String(length=32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["credential_id"], ["capacitas_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capacitas_domande_irrigue_sync_jobs_credential_id", "capacitas_domande_irrigue_sync_jobs", ["credential_id"])
    op.create_index(
        "ix_capacitas_domande_irrigue_sync_jobs_requested_by_user_id",
        "capacitas_domande_irrigue_sync_jobs",
        ["requested_by_user_id"],
    )
    op.create_index("ix_capacitas_domande_irrigue_sync_jobs_status", "capacitas_domande_irrigue_sync_jobs", ["status"])

    op.create_table(
        "cat_domande_irrigue",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("domanda_numero", sa.String(length=50), nullable=True),
        sa.Column("cco", sa.String(length=20), nullable=True),
        sa.Column("com", sa.String(length=10), nullable=True),
        sa.Column("pvc", sa.String(length=10), nullable=True),
        sa.Column("fra", sa.String(length=20), nullable=True),
        sa.Column("ccs", sa.String(length=20), nullable=True),
        sa.Column("idxana", sa.String(length=64), nullable=True),
        sa.Column("source_row_id", sa.String(length=64), nullable=True),
        sa.Column("source_denominazione", sa.String(length=500), nullable=True),
        sa.Column("source_patrimonio", sa.String(length=255), nullable=True),
        sa.Column("patrimonio_has_domanda_hint", sa.Boolean(), nullable=False),
        sa.Column("comune", sa.String(length=100), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("utenza_id", sa.Uuid(), nullable=True),
        sa.Column("occupancy_id", sa.Uuid(), nullable=True),
        sa.Column("stato", sa.String(length=100), nullable=True),
        sa.Column("stato_codice", sa.String(length=20), nullable=True),
        sa.Column("tipo", sa.String(length=100), nullable=True),
        sa.Column("tipo_codice", sa.String(length=20), nullable=True),
        sa.Column("tipo_scheda_codice", sa.String(length=20), nullable=True),
        sa.Column("tipo_scheda", sa.String(length=100), nullable=True),
        sa.Column("autorinnovo", sa.Boolean(), nullable=False),
        sa.Column("ruolo_irr", sa.Numeric(14, 2), nullable=True),
        sa.Column("tot_sup_cat_mq", sa.Numeric(14, 2), nullable=True),
        sa.Column("tot_sup_irr_mq", sa.Numeric(14, 2), nullable=True),
        sa.Column("tot_sup_servita_mq", sa.Numeric(14, 2), nullable=True),
        sa.Column("tot_sup_richiesta_mq", sa.Numeric(14, 2), nullable=True),
        sa.Column("tot_sup_malus_mq", sa.Numeric(14, 2), nullable=True),
        sa.Column("tot_sup_bonus_mq", sa.Numeric(14, 2), nullable=True),
        sa.Column("data_ins", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_agg", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_rett", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_sosp", sa.DateTime(timezone=True), nullable=True),
        sa.Column("data_chius", sa.DateTime(timezone=True), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["occupancy_id"], ["cat_consorzio_occupancies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["utenza_id"], ["cat_utenze_irrigue.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("external_id", name="uq_cat_domande_irrigue_external_id"),
    )
    op.create_index("ix_cat_domande_irrigue_anno", "cat_domande_irrigue", ["anno"])
    op.create_index("ix_cat_domande_irrigue_anno_numero", "cat_domande_irrigue", ["anno", "domanda_numero"])
    op.create_index("ix_cat_domande_irrigue_cco", "cat_domande_irrigue", ["cco"])
    op.create_index("ix_cat_domande_irrigue_com", "cat_domande_irrigue", ["com"])
    op.create_index("ix_cat_domande_irrigue_context", "cat_domande_irrigue", ["cco", "com", "pvc", "fra", "ccs"])
    op.create_index("ix_cat_domande_irrigue_data_ins", "cat_domande_irrigue", ["data_ins"])
    op.create_index("ix_cat_domande_irrigue_domanda_numero", "cat_domande_irrigue", ["domanda_numero"])
    op.create_index("ix_cat_domande_irrigue_idxana", "cat_domande_irrigue", ["idxana"])
    op.create_index("ix_cat_domande_irrigue_occupancy_id", "cat_domande_irrigue", ["occupancy_id"])
    op.create_index("ix_cat_domande_irrigue_stato", "cat_domande_irrigue", ["stato"])
    op.create_index("ix_cat_domande_irrigue_stato_codice", "cat_domande_irrigue", ["stato_codice"])
    op.create_index("ix_cat_domande_irrigue_subject_id", "cat_domande_irrigue", ["subject_id"])
    op.create_index("ix_cat_domande_irrigue_tipo", "cat_domande_irrigue", ["tipo"])
    op.create_index("ix_cat_domande_irrigue_utenza_id", "cat_domande_irrigue", ["utenza_id"])

    op.create_table(
        "cat_domanda_irrigua_particelle",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("domanda_id", sa.Uuid(), nullable=False),
        sa.Column("external_id", sa.String(length=64), nullable=True),
        sa.Column("unit_id", sa.Uuid(), nullable=True),
        sa.Column("segment_id", sa.Uuid(), nullable=True),
        sa.Column("particella_id", sa.Uuid(), nullable=True),
        sa.Column("utenza_id", sa.Uuid(), nullable=True),
        sa.Column("occupancy_id", sa.Uuid(), nullable=True),
        sa.Column("localita", sa.String(length=255), nullable=True),
        sa.Column("comizio", sa.String(length=100), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("sub", sa.String(length=10), nullable=True),
        sa.Column("sup_cat_mq", sa.Numeric(14, 2), nullable=True),
        sa.Column("sup_irr_mq", sa.Numeric(14, 2), nullable=True),
        sa.Column("coltura", sa.String(length=255), nullable=True),
        sa.Column("part_pvc", sa.String(length=10), nullable=True),
        sa.Column("part_com", sa.String(length=10), nullable=True),
        sa.Column("part_cco", sa.String(length=20), nullable=True),
        sa.Column("part_fra", sa.String(length=20), nullable=True),
        sa.Column("part_ccs", sa.String(length=20), nullable=True),
        sa.Column("ruolo_bon", sa.Numeric(14, 2), nullable=True),
        sa.Column("ruolo_irr", sa.Numeric(14, 2), nullable=True),
        sa.Column("ruolo_var", sa.Numeric(14, 2), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["domanda_id"], ["cat_domande_irrigue.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["occupancy_id"], ["cat_consorzio_occupancies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["particella_id"], ["cat_particelle.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["segment_id"], ["cat_consorzio_unit_segments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["cat_consorzio_units.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["utenza_id"], ["cat_utenze_irrigue.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domanda_id", "external_id", name="uq_cat_domanda_irrigua_part_domanda_external"),
    )
    op.create_index("ix_cat_domanda_irrigua_particelle_coltura", "cat_domanda_irrigua_particelle", ["coltura"])
    op.create_index("ix_cat_domanda_irrigua_particelle_domanda_id", "cat_domanda_irrigua_particelle", ["domanda_id"])
    op.create_index("ix_cat_domanda_irrigua_particelle_external_id", "cat_domanda_irrigua_particelle", ["external_id"])
    op.create_index("ix_cat_domanda_irrigua_particelle_foglio", "cat_domanda_irrigua_particelle", ["foglio"])
    op.create_index("ix_cat_domanda_irrigua_part_key", "cat_domanda_irrigua_particelle", ["part_com", "foglio", "particella", "sub"])
    op.create_index("ix_cat_domanda_irrigua_particelle_occupancy_id", "cat_domanda_irrigua_particelle", ["occupancy_id"])
    op.create_index("ix_cat_domanda_irrigua_particelle_part_com", "cat_domanda_irrigua_particelle", ["part_com"])
    op.create_index("ix_cat_domanda_irrigua_particelle_particella", "cat_domanda_irrigua_particelle", ["particella"])
    op.create_index("ix_cat_domanda_irrigua_particelle_particella_id", "cat_domanda_irrigua_particelle", ["particella_id"])
    op.create_index("ix_cat_domanda_irrigua_particelle_segment_id", "cat_domanda_irrigua_particelle", ["segment_id"])
    op.create_index("ix_cat_domanda_irrigua_particelle_unit_id", "cat_domanda_irrigua_particelle", ["unit_id"])
    op.create_index("ix_cat_domanda_irrigua_particelle_utenza_id", "cat_domanda_irrigua_particelle", ["utenza_id"])


def downgrade() -> None:
    op.drop_index("ix_cat_domanda_irrigua_particelle_utenza_id", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_unit_id", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_segment_id", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_particella_id", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_particella", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_part_com", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_occupancy_id", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_part_key", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_foglio", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_external_id", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_domanda_id", table_name="cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domanda_irrigua_particelle_coltura", table_name="cat_domanda_irrigua_particelle")
    op.drop_table("cat_domanda_irrigua_particelle")
    op.drop_index("ix_cat_domande_irrigue_utenza_id", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_tipo", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_subject_id", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_stato_codice", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_stato", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_occupancy_id", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_idxana", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_domanda_numero", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_data_ins", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_context", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_com", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_cco", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_anno_numero", table_name="cat_domande_irrigue")
    op.drop_index("ix_cat_domande_irrigue_anno", table_name="cat_domande_irrigue")
    op.drop_table("cat_domande_irrigue")
    op.drop_index("ix_capacitas_domande_irrigue_sync_jobs_status", table_name="capacitas_domande_irrigue_sync_jobs")
    op.drop_index(
        "ix_capacitas_domande_irrigue_sync_jobs_requested_by_user_id",
        table_name="capacitas_domande_irrigue_sync_jobs",
    )
    op.drop_index("ix_capacitas_domande_irrigue_sync_jobs_credential_id", table_name="capacitas_domande_irrigue_sync_jobs")
    op.drop_table("capacitas_domande_irrigue_sync_jobs")
