"""add incass payment notices and sync jobs

Revision ID: 20260521_0092
Revises: 20260521_0091
Create Date: 2026-05-21
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260521_0092"
down_revision: Union[str, Sequence[str], None] = "20260521_0091"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "capacitas_incass_sync_jobs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("credential_id", sa.Integer(), nullable=True),
        sa.Column("requested_by_user_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("mode", sa.String(length=32), nullable=False, server_default="subjects_sync"),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["credential_id"], ["capacitas_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["requested_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_capacitas_incass_sync_jobs_credential_id", "capacitas_incass_sync_jobs", ["credential_id"], unique=False)
    op.create_index("ix_capacitas_incass_sync_jobs_requested_by_user_id", "capacitas_incass_sync_jobs", ["requested_by_user_id"], unique=False)
    op.create_index("ix_capacitas_incass_sync_jobs_status", "capacitas_incass_sync_jobs", ["status"], unique=False)

    op.create_table(
        "ana_payment_notices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("source_system", sa.String(length=32), nullable=False, server_default="incass"),
        sa.Column("source_notice_id", sa.String(length=128), nullable=False),
        sa.Column("source_internal_id", sa.String(length=128), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=True),
        sa.Column("partita_iva", sa.String(length=32), nullable=True),
        sa.Column("display_name", sa.String(length=512), nullable=True),
        sa.Column("anno", sa.String(length=16), nullable=True),
        sa.Column("stato_code", sa.String(length=64), nullable=True),
        sa.Column("stato_label", sa.String(length=128), nullable=True),
        sa.Column("data_scadenza", sa.Date(), nullable=True),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        sa.Column("tipo_anagrafica", sa.String(length=64), nullable=True),
        sa.Column("ultimo_invio", sa.String(length=64), nullable=True),
        sa.Column("lista_id", sa.String(length=128), nullable=True),
        sa.Column("lista_descrizione", sa.String(length=255), nullable=True),
        sa.Column("indirizzo", sa.String(length=512), nullable=True),
        sa.Column("cap", sa.String(length=16), nullable=True),
        sa.Column("citta", sa.String(length=255), nullable=True),
        sa.Column("provincia", sa.String(length=16), nullable=True),
        sa.Column("importo_carico", sa.String(length=64), nullable=True),
        sa.Column("importo_sgravio", sa.String(length=64), nullable=True),
        sa.Column("importo_riscosso", sa.String(length=64), nullable=True),
        sa.Column("importo_residuo", sa.String(length=64), nullable=True),
        sa.Column("importo_riporto", sa.String(length=64), nullable=True),
        sa.Column("importo_rateizzato", sa.String(length=64), nullable=True),
        sa.Column("importo_annullato", sa.String(length=64), nullable=True),
        sa.Column("detail_url", sa.String(length=1024), nullable=True),
        sa.Column("detail_info_html", sa.Text(), nullable=True),
        sa.Column("detail_info_text", sa.Text(), nullable=True),
        sa.Column("pdf_links_json", sa.JSON(), nullable=True),
        sa.Column("raw_row_json", sa.JSON(), nullable=True),
        sa.Column("raw_detail_json", sa.JSON(), nullable=True),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source_system", "source_notice_id", name="uq_ana_payment_notices_source_notice"),
    )
    op.create_index("ix_ana_payment_notices_subject_id", "ana_payment_notices", ["subject_id"], unique=False)
    op.create_index("ix_ana_payment_notices_source_system", "ana_payment_notices", ["source_system"], unique=False)
    op.create_index("ix_ana_payment_notices_source_notice_id", "ana_payment_notices", ["source_notice_id"], unique=False)
    op.create_index("ix_ana_payment_notices_source_internal_id", "ana_payment_notices", ["source_internal_id"], unique=False)
    op.create_index("ix_ana_payment_notices_codice_fiscale", "ana_payment_notices", ["codice_fiscale"], unique=False)
    op.create_index("ix_ana_payment_notices_partita_iva", "ana_payment_notices", ["partita_iva"], unique=False)
    op.create_index("ix_ana_payment_notices_display_name", "ana_payment_notices", ["display_name"], unique=False)
    op.create_index("ix_ana_payment_notices_anno", "ana_payment_notices", ["anno"], unique=False)
    op.create_index("ix_ana_payment_notices_stato_code", "ana_payment_notices", ["stato_code"], unique=False)
    op.create_index("ix_ana_payment_notices_data_scadenza", "ana_payment_notices", ["data_scadenza"], unique=False)
    op.create_index("ix_ana_payment_notices_synced_at", "ana_payment_notices", ["synced_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_ana_payment_notices_synced_at", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_data_scadenza", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_stato_code", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_anno", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_display_name", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_partita_iva", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_codice_fiscale", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_source_internal_id", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_source_notice_id", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_source_system", table_name="ana_payment_notices")
    op.drop_index("ix_ana_payment_notices_subject_id", table_name="ana_payment_notices")
    op.drop_table("ana_payment_notices")

    op.drop_index("ix_capacitas_incass_sync_jobs_status", table_name="capacitas_incass_sync_jobs")
    op.drop_index("ix_capacitas_incass_sync_jobs_requested_by_user_id", table_name="capacitas_incass_sync_jobs")
    op.drop_index("ix_capacitas_incass_sync_jobs_credential_id", table_name="capacitas_incass_sync_jobs")
    op.drop_table("capacitas_incass_sync_jobs")
