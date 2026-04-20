"""catasto phase1 postgis and tables

Revision ID: 20260420_0051
Revises: 20260417_0050
Create Date: 2026-04-20
"""

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry


revision = "20260420_0051"
down_revision = "20260417_0050"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis_topology;")

    op.create_table(
        "cat_import_batches",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("tipo", sa.String(length=20), nullable=False),
        sa.Column("anno_campagna", sa.Integer(), nullable=True),
        sa.Column("hash_file", sa.String(length=64), nullable=True),
        sa.Column("righe_totali", sa.Integer(), server_default="0", nullable=False),
        sa.Column("righe_importate", sa.Integer(), server_default="0", nullable=False),
        sa.Column("righe_anomalie", sa.Integer(), server_default="0", nullable=False),
        sa.Column("status", sa.String(length=20), server_default=sa.text("'processing'"), nullable=False),
        sa.Column("report_json", sa.JSON(), nullable=True),
        sa.Column("errore", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "cat_schemi_contributo",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("codice", sa.String(length=10), nullable=False),
        sa.Column("descrizione", sa.String(length=200), nullable=True),
        sa.Column("tipo_calcolo", sa.String(length=20), server_default=sa.text("'fisso'"), nullable=False),
        sa.Column("attivo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codice"),
    )

    op.create_table(
        "cat_aliquote",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("schema_id", sa.Uuid(), sa.ForeignKey("cat_schemi_contributo.id"), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("aliquota", sa.Numeric(precision=10, scale=6), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("schema_id", "anno", name="uq_cat_aliquote_schema_anno"),
    )

    op.create_table(
        "cat_distretti",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("num_distretto", sa.String(length=10), nullable=False),
        sa.Column("nome_distretto", sa.String(length=200), nullable=True),
        sa.Column("decreto_istitutivo", sa.String(length=200), nullable=True),
        sa.Column("data_decreto", sa.Date(), nullable=True),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("attivo", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("num_distretto"),
    )
    op.create_index("idx_cat_distretti_geom", "cat_distretti", ["geometry"], unique=False, postgresql_using="gist")

    op.create_table(
        "cat_distretto_coefficienti",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("distretto_id", sa.Uuid(), sa.ForeignKey("cat_distretti.id"), nullable=False),
        sa.Column("anno", sa.Integer(), nullable=False),
        sa.Column("ind_spese_fisse", sa.Numeric(precision=6, scale=4), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("distretto_id", "anno", name="uq_cat_dc_distretto_anno"),
    )

    op.create_table(
        "cat_particelle",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("national_code", sa.String(length=25), nullable=True),
        sa.Column("cod_comune_istat", sa.Integer(), nullable=False),
        sa.Column("nome_comune", sa.String(length=100), nullable=True),
        sa.Column("sezione_catastale", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=False),
        sa.Column("particella", sa.String(length=20), nullable=False),
        sa.Column("subalterno", sa.String(length=10), nullable=True),
        sa.Column("cfm", sa.String(length=30), nullable=True),
        sa.Column("superficie_mq", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("num_distretto", sa.String(length=10), nullable=True),
        sa.Column("nome_distretto", sa.String(length=100), nullable=True),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("source_type", sa.String(length=20), server_default=sa.text("'shapefile'"), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("valid_from", sa.Date(), server_default=sa.text("CURRENT_DATE"), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("suppressed", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_cat_part_geom",
        "cat_particelle",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "idx_cat_part_distretto",
        "cat_particelle",
        ["num_distretto"],
        unique=False,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "idx_cat_part_cfm",
        "cat_particelle",
        ["cfm"],
        unique=False,
        postgresql_where=sa.text("is_current = true"),
    )
    op.create_index(
        "idx_cat_part_lookup",
        "cat_particelle",
        ["cod_comune_istat", "foglio", "particella", "subalterno"],
        unique=False,
        postgresql_where=sa.text("is_current = true"),
    )

    op.create_table(
        "cat_particelle_history",
        sa.Column("history_id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("particella_id", sa.Uuid(), nullable=False),
        sa.Column("national_code", sa.String(length=25), nullable=True),
        sa.Column("cod_comune_istat", sa.Integer(), nullable=False),
        sa.Column("foglio", sa.String(length=10), nullable=False),
        sa.Column("particella", sa.String(length=20), nullable=False),
        sa.Column("subalterno", sa.String(length=10), nullable=True),
        sa.Column("superficie_mq", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("num_distretto", sa.String(length=10), nullable=True),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=True),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=False),
        sa.Column("changed_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("change_reason", sa.String(length=50), nullable=True),
        sa.PrimaryKeyConstraint("history_id"),
    )

    op.create_table(
        "cat_utenze_irrigue",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), sa.ForeignKey("cat_import_batches.id", ondelete="CASCADE"), nullable=False),
        sa.Column("anno_campagna", sa.Integer(), nullable=False),
        sa.Column("cco", sa.String(length=20), nullable=True),
        sa.Column("cod_provincia", sa.Integer(), nullable=True),
        sa.Column("cod_comune_istat", sa.Integer(), nullable=True),
        sa.Column("cod_frazione", sa.Integer(), nullable=True),
        sa.Column("num_distretto", sa.Integer(), nullable=True),
        sa.Column("nome_distretto_loc", sa.String(length=200), nullable=True),
        sa.Column("nome_comune", sa.String(length=100), nullable=True),
        sa.Column("sezione_catastale", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("subalterno", sa.String(length=10), nullable=True),
        sa.Column("particella_id", sa.Uuid(), sa.ForeignKey("cat_particelle.id"), nullable=True),
        sa.Column("sup_catastale_mq", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("sup_irrigabile_mq", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("ind_spese_fisse", sa.Numeric(precision=6, scale=4), nullable=True),
        sa.Column("imponibile_sf", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("esente_0648", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("aliquota_0648", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("importo_0648", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("aliquota_0985", sa.Numeric(precision=10, scale=6), nullable=True),
        sa.Column("importo_0985", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("denominazione", sa.String(length=500), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=16), nullable=True),
        sa.Column("codice_fiscale_raw", sa.String(length=16), nullable=True),
        sa.Column("anomalia_superficie", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("anomalia_cf_invalido", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("anomalia_cf_mancante", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("anomalia_comune_invalido", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("anomalia_particella_assente", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("anomalia_imponibile", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("anomalia_importi", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cat_utenze_batch", "cat_utenze_irrigue", ["import_batch_id"], unique=False)
    op.create_index("idx_cat_utenze_anno", "cat_utenze_irrigue", ["anno_campagna"], unique=False)
    op.create_index("idx_cat_utenze_distretto", "cat_utenze_irrigue", ["num_distretto"], unique=False)
    op.create_index("idx_cat_utenze_cf", "cat_utenze_irrigue", ["codice_fiscale"], unique=False)

    op.create_table(
        "cat_intestatari",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("codice_fiscale", sa.String(length=16), nullable=False),
        sa.Column("denominazione", sa.String(length=500), nullable=True),
        sa.Column("tipo", sa.String(length=5), nullable=True),
        sa.Column("cognome", sa.String(length=100), nullable=True),
        sa.Column("nome", sa.String(length=100), nullable=True),
        sa.Column("data_nascita", sa.Date(), nullable=True),
        sa.Column("luogo_nascita", sa.String(length=100), nullable=True),
        sa.Column("ragione_sociale", sa.String(length=500), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=True),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deceduto", sa.Boolean(), nullable=True),
        sa.Column("dati_sister_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codice_fiscale"),
    )

    op.create_table(
        "cat_anomalie",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("particella_id", sa.Uuid(), sa.ForeignKey("cat_particelle.id"), nullable=True),
        sa.Column("utenza_id", sa.Uuid(), sa.ForeignKey("cat_utenze_irrigue.id"), nullable=True),
        sa.Column("anno_campagna", sa.Integer(), nullable=True),
        sa.Column("tipo", sa.String(length=50), nullable=False),
        sa.Column("severita", sa.String(length=10), nullable=False),
        sa.Column("descrizione", sa.Text(), nullable=True),
        sa.Column("dati_json", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(length=25), server_default=sa.text("'aperta'"), nullable=False),
        sa.Column("note_operatore", sa.Text(), nullable=True),
        sa.Column("assigned_to", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("segnalazione_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_cat_anomalie_particella", "cat_anomalie", ["particella_id"], unique=False)
    op.create_index("idx_cat_anomalie_tipo", "cat_anomalie", ["tipo"], unique=False)
    op.create_index("idx_cat_anomalie_status", "cat_anomalie", ["status"], unique=False)
    op.create_index("idx_cat_anomalie_anno", "cat_anomalie", ["anno_campagna"], unique=False)

    op.execute(
        """
        INSERT INTO cat_schemi_contributo (id, codice, descrizione, tipo_calcolo, attivo) VALUES
        (gen_random_uuid(), '0648', 'Contributo Irriguo - Opere Irrigue', 'fisso', true),
        (gen_random_uuid(), '0985', 'Quote Ordinarie Consorzio - Costo Variabile Contatori', 'contatori', true)
        ON CONFLICT (codice) DO NOTHING
        """
    )


def downgrade() -> None:
    op.drop_index("idx_cat_anomalie_anno", table_name="cat_anomalie")
    op.drop_index("idx_cat_anomalie_status", table_name="cat_anomalie")
    op.drop_index("idx_cat_anomalie_tipo", table_name="cat_anomalie")
    op.drop_index("idx_cat_anomalie_particella", table_name="cat_anomalie")
    op.drop_table("cat_anomalie")

    op.drop_table("cat_intestatari")

    op.drop_index("idx_cat_utenze_cf", table_name="cat_utenze_irrigue")
    op.drop_index("idx_cat_utenze_distretto", table_name="cat_utenze_irrigue")
    op.drop_index("idx_cat_utenze_anno", table_name="cat_utenze_irrigue")
    op.drop_index("idx_cat_utenze_batch", table_name="cat_utenze_irrigue")
    op.drop_table("cat_utenze_irrigue")

    op.drop_table("cat_particelle_history")

    op.drop_index("idx_cat_part_lookup", table_name="cat_particelle")
    op.drop_index("idx_cat_part_cfm", table_name="cat_particelle")
    op.drop_index("idx_cat_part_distretto", table_name="cat_particelle")
    op.drop_index("idx_cat_part_geom", table_name="cat_particelle")
    op.drop_table("cat_particelle")

    op.drop_table("cat_distretto_coefficienti")

    op.drop_index("idx_cat_distretti_geom", table_name="cat_distretti")
    op.drop_table("cat_distretti")

    op.drop_table("cat_aliquote")
    op.drop_table("cat_schemi_contributo")
    op.drop_table("cat_import_batches")
