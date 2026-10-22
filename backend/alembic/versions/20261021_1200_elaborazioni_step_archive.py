"""elaborazioni STEP credentials, jobs and read-only archive

Revision ID: 20261021_1200
Revises: 20261019_1500
Create Date: 2026-10-21
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20261021_1200"
down_revision = "20261019_1500"
branch_labels = None
depends_on = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def _amount(name: str) -> sa.Column:
    return sa.Column(name, sa.Numeric(14, 2), nullable=True)


def upgrade() -> None:
    op.create_table(
        "step_credentials",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("password_encrypted", sa.Text(), nullable=False),
        sa.Column("portal_url", sa.String(500), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("min_delay_ms", sa.Integer(), nullable=False),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("consecutive_failures", sa.Integer(), nullable=False),
        *_timestamps(),
    )
    op.create_index("ix_step_credentials_active", "step_credentials", ["active"])

    op.create_table(
        "step_sync_jobs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "credential_id", sa.Integer(), sa.ForeignKey("step_credentials.id", ondelete="SET NULL")
        ),
        sa.Column(
            "requested_by_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="SET NULL"),
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
    )
    for column in ("credential_id", "requested_by_user_id", "status"):
        op.create_index(f"ix_step_sync_jobs_{column}", "step_sync_jobs", [column])

    op.create_table(
        "step_contribuenti",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("cod_ent", sa.String(20), nullable=False),
        sa.Column("codice_fiscale", sa.String(32), nullable=False),
        sa.Column("tipo_anagrafica", sa.String(8), nullable=True),
        sa.Column("denominazione", sa.String(300), nullable=True),
        sa.Column("numero_documenti", sa.Integer(), nullable=True),
        _amount("importo"),
        _amount("pagato"),
        _amount("residuo"),
        _amount("importo_aggiornato"),
        sa.Column("stato_documenti", sa.String(80), nullable=True),
        sa.Column("anagrafica_json", sa.JSON(), nullable=True),
        sa.Column("situazione_contabile_json", sa.JSON(), nullable=True),
        sa.Column("sections_json", sa.JSON(), nullable=True),
        sa.Column("summary_raw_json", sa.JSON(), nullable=False),
        sa.Column("summary_fingerprint", sa.String(64), nullable=False),
        sa.Column("detail_fingerprint", sa.String(64), nullable=True),
        sa.Column("document_reconciliation_json", sa.JSON(), nullable=True),
        sa.Column(
            "last_seen_job_id",
            sa.Integer(),
            sa.ForeignKey("step_sync_jobs.id", ondelete="SET NULL"),
        ),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("detail_synced_at", sa.DateTime(timezone=True), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint("cod_ent", "codice_fiscale", name="uq_step_contribuente_ente_cf"),
    )
    for column in ("codice_fiscale", "denominazione", "stato_documenti", "last_seen_job_id"):
        op.create_index(f"ix_step_contribuenti_{column}", "step_contribuenti", [column])

    op.create_table(
        "step_documenti",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "contribuente_id",
            sa.Uuid(),
            sa.ForeignKey("step_contribuenti.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("num_doc", sa.String(40), nullable=False),
        sa.Column("prg_coo", sa.String(10), nullable=False),
        sa.Column("section", sa.String(120), nullable=True),
        sa.Column("tipo_lista", sa.String(10), nullable=True),
        sa.Column("cod_trib", sa.String(10), nullable=True),
        sa.Column("des_trib", sa.String(300), nullable=True),
        sa.Column("des_doc", sa.String(300), nullable=True),
        sa.Column("anno_rif", sa.String(60), nullable=True),
        sa.Column("data_notifica", sa.Date(), nullable=True),
        _amount("tot_dovuto"),
        _amount("imp_carico"),
        _amount("imp_discaricato"),
        _amount("tot_pagato"),
        _amount("residuo"),
        sa.Column("num_tributi", sa.Integer(), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column("source_fingerprint", sa.String(64), nullable=False),
        sa.Column("pdf_status", sa.String(20), nullable=False),
        sa.Column("pdf_path", sa.String(500), nullable=True),
        sa.Column("pdf_sha256", sa.String(64), nullable=True),
        sa.Column("pdf_bytes", sa.Integer(), nullable=True),
        sa.Column("pdf_original_filename", sa.String(300), nullable=True),
        sa.Column("pdf_unavailable_reason", sa.Text(), nullable=True),
        *_timestamps(),
        sa.UniqueConstraint(
            "contribuente_id", "num_doc", "prg_coo", name="uq_step_documento_contribuente_doc"
        ),
    )
    for column in ("contribuente_id", "num_doc", "cod_trib"):
        op.create_index(f"ix_step_documenti_{column}", "step_documenti", [column])

    op.create_table(
        "step_tributi",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "documento_id",
            sa.Uuid(),
            sa.ForeignKey("step_documenti.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("partita", sa.String(40), nullable=True),
        sa.Column("prg", sa.String(10), nullable=True),
        sa.Column("cod_tributo", sa.String(10), nullable=True),
        sa.Column("des_tributo", sa.String(300), nullable=True),
        sa.Column("tipo_tributo", sa.String(60), nullable=True),
        sa.Column("anno_rif", sa.Integer(), nullable=True),
        _amount("imp_carico"),
        _amount("imp_carico_pagato"),
        _amount("imp_discaricato"),
        sa.Column("avviso_reference_raw", sa.String(300), nullable=True),
        sa.Column("codice_cnc", sa.String(50), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("documento_id", "position", name="uq_step_tributo_documento_position"),
    )
    for column in ("documento_id", "cod_tributo", "anno_rif", "codice_cnc"):
        op.create_index(f"ix_step_tributi_{column}", "step_tributi", [column])

    op.create_table(
        "step_pagamenti",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "contribuente_id",
            sa.Uuid(),
            sa.ForeignKey("step_contribuenti.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "documento_id",
            sa.Uuid(),
            sa.ForeignKey("step_documenti.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("num_quietanza", sa.String(40), nullable=True),
        sa.Column("num_doc", sa.String(40), nullable=True),
        sa.Column("data_pagamento", sa.Date(), nullable=True),
        sa.Column("data_accredito", sa.Date(), nullable=True),
        sa.Column("modalita", sa.String(80), nullable=True),
        _amount("importo"),
        _amount("importo_pagato"),
        sa.Column("annullato", sa.Boolean(), nullable=False),
        sa.Column("stato", sa.String(60), nullable=True),
        sa.Column("riferimento", sa.String(300), nullable=True),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint(
            "contribuente_id", "position", name="uq_step_pagamento_contribuente_position"
        ),
    )
    for column in ("contribuente_id", "documento_id", "num_quietanza"):
        op.create_index(f"ix_step_pagamenti_{column}", "step_pagamenti", [column])

    op.create_table(
        "step_observations",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "contribuente_id",
            sa.Uuid(),
            sa.ForeignKey("step_contribuenti.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "job_id",
            sa.Integer(),
            sa.ForeignKey("step_sync_jobs.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_step_observations_contribuente_id", "step_observations", ["contribuente_id"]
    )
    op.create_index("ix_step_observations_job_id", "step_observations", ["job_id"])

    op.create_table(
        "step_ruolo_links",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "documento_id",
            sa.Uuid(),
            sa.ForeignKey("step_documenti.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("reference_key", sa.String(300), nullable=False),
        sa.Column("codice_cnc", sa.String(50), nullable=True),
        sa.Column("anno_rif", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column(
            "ruolo_avviso_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_avvisi.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("candidate_avviso_ids", sa.JSON(), nullable=True),
        sa.Column("tributi_count", sa.Integer(), nullable=False),
        _amount("imp_carico"),
        _amount("imp_carico_pagato"),
        _amount("imp_discaricato"),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "documento_id", "reference_key", name="uq_step_ruolo_link_documento_reference"
        ),
    )
    for column in ("documento_id", "codice_cnc", "status", "ruolo_avviso_id"):
        op.create_index(f"ix_step_ruolo_links_{column}", "step_ruolo_links", [column])


def downgrade() -> None:
    for table in (
        "step_ruolo_links",
        "step_observations",
        "step_pagamenti",
        "step_tributi",
        "step_documenti",
        "step_contribuenti",
        "step_sync_jobs",
        "step_credentials",
    ):
        op.drop_table(table)
