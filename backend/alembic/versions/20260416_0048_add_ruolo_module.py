"""add ruolo module

Revision ID: 20260416_0048
Revises: 20260416_0047
Create Date: 2026-04-16
"""

from alembic import op
import sqlalchemy as sa


revision = "20260416_0048"
down_revision = "20260416_0047"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. ruolo_import_jobs
    op.create_table(
        "ruolo_import_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("anno_tributario", sa.Integer(), nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("total_partite", sa.Integer(), nullable=True),
        sa.Column("records_imported", sa.Integer(), nullable=True),
        sa.Column("records_skipped", sa.Integer(), nullable=True),
        sa.Column("records_errors", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.Integer(), nullable=True),
        sa.Column("params_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["triggered_by"], ["application_users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ruolo_import_jobs_anno_tributario"), "ruolo_import_jobs", ["anno_tributario"], unique=False)
    op.create_index(op.f("ix_ruolo_import_jobs_status"), "ruolo_import_jobs", ["status"], unique=False)

    # 2. ruolo_avvisi
    op.create_table(
        "ruolo_avvisi",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=False),
        sa.Column("codice_cnc", sa.String(length=50), nullable=False),
        sa.Column("anno_tributario", sa.Integer(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("codice_fiscale_raw", sa.String(length=20), nullable=True),
        sa.Column("nominativo_raw", sa.String(length=300), nullable=True),
        sa.Column("domicilio_raw", sa.Text(), nullable=True),
        sa.Column("residenza_raw", sa.Text(), nullable=True),
        sa.Column("n2_extra_raw", sa.String(length=100), nullable=True),
        sa.Column("codice_utenza", sa.String(length=30), nullable=True),
        sa.Column("importo_totale_0648", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("importo_totale_0985", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("importo_totale_0668", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("importo_totale_euro", sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column("importo_totale_lire", sa.Numeric(precision=14, scale=2), nullable=True),
        sa.Column("n4_campo_sconosciuto", sa.String(length=30), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["import_job_id"], ["ruolo_import_jobs.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codice_cnc", "anno_tributario", name="uq_ruolo_avvisi_cnc_anno"),
    )
    op.create_index(op.f("ix_ruolo_avvisi_subject_id"), "ruolo_avvisi", ["subject_id"], unique=False)
    op.create_index(op.f("ix_ruolo_avvisi_codice_fiscale_raw"), "ruolo_avvisi", ["codice_fiscale_raw"], unique=False)
    op.create_index(op.f("ix_ruolo_avvisi_anno_tributario"), "ruolo_avvisi", ["anno_tributario"], unique=False)

    # 3. ruolo_partite
    op.create_table(
        "ruolo_partite",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("avviso_id", sa.Uuid(), nullable=False),
        sa.Column("codice_partita", sa.String(length=30), nullable=False),
        sa.Column("comune_nome", sa.String(length=100), nullable=False),
        sa.Column("comune_codice", sa.String(length=10), nullable=True),
        sa.Column("contribuente_cf", sa.String(length=20), nullable=True),
        sa.Column("co_intestati_raw", sa.Text(), nullable=True),
        sa.Column("importo_0648", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("importo_0985", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("importo_0668", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["avviso_id"], ["ruolo_avvisi.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ruolo_partite_avviso_id"), "ruolo_partite", ["avviso_id"], unique=False)
    op.create_index(op.f("ix_ruolo_partite_codice_partita"), "ruolo_partite", ["codice_partita"], unique=False)

    # 4. ruolo_particelle (prima catasto_parcels non esiste ancora, sarà creata dopo)
    op.create_table(
        "ruolo_particelle",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("partita_id", sa.Uuid(), nullable=False),
        sa.Column("anno_tributario", sa.Integer(), nullable=False),
        sa.Column("domanda_irrigua", sa.String(length=10), nullable=True),
        sa.Column("distretto", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=False),
        sa.Column("particella", sa.String(length=20), nullable=False),
        sa.Column("subalterno", sa.String(length=10), nullable=True),
        sa.Column("sup_catastale_are", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("sup_catastale_ha", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("sup_irrigata_ha", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("coltura", sa.String(length=50), nullable=True),
        sa.Column("importo_manut", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("importo_irrig", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("importo_ist", sa.Numeric(precision=10, scale=2), nullable=True),
        sa.Column("catasto_parcel_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["partita_id"], ["ruolo_partite.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ruolo_particelle_partita_id"), "ruolo_particelle", ["partita_id"], unique=False)
    op.create_index(
        op.f("ix_ruolo_particelle_anno_foglio_particella"),
        "ruolo_particelle",
        ["anno_tributario", "foglio", "particella"],
        unique=False,
    )
    op.create_index(op.f("ix_ruolo_particelle_catasto_parcel_id"), "ruolo_particelle", ["catasto_parcel_id"], unique=False)

    # 5. catasto_parcels
    op.create_table(
        "catasto_parcels",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("comune_codice", sa.String(length=10), nullable=False),
        sa.Column("comune_nome", sa.String(length=100), nullable=False),
        sa.Column("foglio", sa.String(length=10), nullable=False),
        sa.Column("particella", sa.String(length=20), nullable=False),
        sa.Column("subalterno", sa.String(length=10), nullable=True),
        sa.Column("sup_catastale_are", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("sup_catastale_ha", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.Column("valid_from", sa.Integer(), nullable=False),
        sa.Column("valid_to", sa.Integer(), nullable=True),
        sa.Column("source", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "comune_codice", "foglio", "particella", "subalterno", "valid_from",
            name="uq_catasto_parcels_key_from",
        ),
    )
    op.create_index(
        op.f("ix_catasto_parcels_comune_foglio_particella"),
        "catasto_parcels",
        ["comune_codice", "foglio", "particella"],
        unique=False,
    )
    op.create_index(op.f("ix_catasto_parcels_valid_to"), "catasto_parcels", ["valid_to"], unique=False)

    # Now add FK from ruolo_particelle → catasto_parcels
    op.create_foreign_key(
        "fk_ruolo_particelle_catasto_parcel_id",
        "ruolo_particelle",
        "catasto_parcels",
        ["catasto_parcel_id"],
        ["id"],
        ondelete="SET NULL",
    )

    # Add module_ruolo column to application_users
    op.add_column("application_users", sa.Column("module_ruolo", sa.Boolean(), nullable=False, server_default="false"))


def downgrade() -> None:
    op.drop_column("application_users", "module_ruolo")

    op.drop_constraint("fk_ruolo_particelle_catasto_parcel_id", "ruolo_particelle", type_="foreignkey")

    op.drop_index(op.f("ix_catasto_parcels_valid_to"), table_name="catasto_parcels")
    op.drop_index(op.f("ix_catasto_parcels_comune_foglio_particella"), table_name="catasto_parcels")
    op.drop_table("catasto_parcels")

    op.drop_index(op.f("ix_ruolo_particelle_catasto_parcel_id"), table_name="ruolo_particelle")
    op.drop_index(op.f("ix_ruolo_particelle_anno_foglio_particella"), table_name="ruolo_particelle")
    op.drop_index(op.f("ix_ruolo_particelle_partita_id"), table_name="ruolo_particelle")
    op.drop_table("ruolo_particelle")

    op.drop_index(op.f("ix_ruolo_partite_codice_partita"), table_name="ruolo_partite")
    op.drop_index(op.f("ix_ruolo_partite_avviso_id"), table_name="ruolo_partite")
    op.drop_table("ruolo_partite")

    op.drop_index(op.f("ix_ruolo_avvisi_anno_tributario"), table_name="ruolo_avvisi")
    op.drop_index(op.f("ix_ruolo_avvisi_codice_fiscale_raw"), table_name="ruolo_avvisi")
    op.drop_index(op.f("ix_ruolo_avvisi_subject_id"), table_name="ruolo_avvisi")
    op.drop_table("ruolo_avvisi")

    op.drop_index(op.f("ix_ruolo_import_jobs_status"), table_name="ruolo_import_jobs")
    op.drop_index(op.f("ix_ruolo_import_jobs_anno_tributario"), table_name="ruolo_import_jobs")
    op.drop_table("ruolo_import_jobs")
