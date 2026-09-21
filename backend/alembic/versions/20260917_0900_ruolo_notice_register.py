"""Add the operational notice register without importing data or enabling sends."""

import sqlalchemy as sa
from alembic import op

revision = "20260917_0900"
down_revision = "20260915_1400"
branch_labels = None
depends_on = None


def _id():
    return sa.Column("id", sa.Uuid(), primary_key=True)


def _document_id(primary_key=False):
    return sa.Column(
        "document_id", sa.Uuid(),
        sa.ForeignKey("ruolo_notice_documents.id", ondelete="RESTRICT"),
        nullable=False, primary_key=primary_key,
    )


def _source():
    return [
        sa.Column("source_system", sa.String(40), nullable=False),
        sa.Column("source_key", sa.String(200), nullable=False),
    ]


def upgrade():
    op.create_table(
        "ruolo_notice_documents", _id(), *_source(),
        sa.Column("document_number", sa.String(100), nullable=False),
        sa.Column("tax_code", sa.String(20)),
        sa.Column("issued_on", sa.Date()),
        sa.Column("original_json", sa.JSON(), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("source_system", "source_key", name="uq_notice_document_source"),
        sa.CheckConstraint("version > 0", name="ck_notice_document_version"),
    )
    op.create_table(
        "ruolo_notice_positions", _id(), _document_id(),
        sa.Column("source_namespace", sa.String(40), nullable=False),
        sa.Column("source_reference", sa.String(100), nullable=False),
        sa.Column("tax_year", sa.Integer(), nullable=False),
        sa.Column("avviso_id", sa.Uuid(), sa.ForeignKey("ruolo_avvisi.id", ondelete="RESTRICT")),
        sa.UniqueConstraint("document_id", "source_namespace", "source_reference", "tax_year", name="uq_notice_position_source"),
        sa.UniqueConstraint("document_id", "avviso_id", name="uq_notice_position_avviso"),
        sa.CheckConstraint("tax_year BETWEEN 1900 AND 9999", name="ck_notice_position_year"),
    )
    op.create_table(
        "ruolo_notice_attempts", _id(), _document_id(), *_source(),
        sa.Column("channel", sa.String(40), nullable=False),
        sa.Column("tracking_code", sa.String(100)),
        sa.Column("sent_at", sa.DateTime(timezone=True)),
        sa.Column("registered_mail_id", sa.Uuid(), sa.ForeignKey("ruolo_tributi_registered_mails.id", ondelete="RESTRICT"), unique=True),
        sa.UniqueConstraint("document_id", "id", name="uq_notice_attempt_document"),
        sa.UniqueConstraint("source_system", "source_key", name="uq_notice_attempt_source"),
    )
    op.create_table(
        "ruolo_notice_evidence", _id(), _document_id(), *_source(),
        sa.Column("attempt_id", sa.Uuid()),
        sa.Column("kind", sa.String(60), nullable=False),
        sa.Column("occurred_on", sa.Date()),
        sa.Column("reference", sa.Text(), nullable=False),
        sa.Column("original_json", sa.JSON(), nullable=False),
        sa.UniqueConstraint("document_id", "id", name="uq_notice_evidence_document"),
        sa.UniqueConstraint("source_system", "source_key", name="uq_notice_evidence_source"),
        sa.ForeignKeyConstraint(
            ["document_id", "attempt_id"], ["ruolo_notice_attempts.document_id", "ruolo_notice_attempts.id"],
            name="fk_notice_evidence_attempt", ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "ruolo_notice_notifications", _document_id(primary_key=True),
        sa.Column("state", sa.String(40), nullable=False, server_default="da_verificare"),
        sa.Column("notified_on", sa.Date()),
        sa.Column("evidence_id", sa.Uuid()),
        sa.CheckConstraint(
            "state IN ('nessuna_evidenza', 'invio_in_corso', 'tentativo_senza_notifica', 'perfezionata', 'da_verificare')",
            name="ck_notice_notification_state",
        ),
        sa.CheckConstraint(
            "(state = 'perfezionata' AND notified_on IS NOT NULL AND evidence_id IS NOT NULL) OR (state <> 'perfezionata' AND notified_on IS NULL)",
            name="ck_notice_notification_proof",
        ),
        sa.ForeignKeyConstraint(
            ["document_id", "evidence_id"], ["ruolo_notice_evidence.document_id", "ruolo_notice_evidence.id"],
            name="fk_notice_notification_evidence", ondelete="RESTRICT",
        ),
    )
    op.create_table(
        "ruolo_notice_recoveries",
        sa.Column("position_id", sa.Uuid(), sa.ForeignKey("ruolo_notice_positions.id", ondelete="RESTRICT"), primary_key=True),
        sa.Column("state", sa.String(40), nullable=False, server_default="da_verificare"),
        sa.Column("case_reference", sa.String(200)),
        sa.Column("verified_on", sa.Date()),
        sa.Column("evidence_reference", sa.Text()),
        sa.Column("amount", sa.Numeric(14, 2)),
        sa.CheckConstraint(
            "state IN ('da_verificare', 'non_affidato_verificato', 'affidato', 'revocato', 'chiuso')",
            name="ck_notice_recovery_state",
        ),
        sa.CheckConstraint(
            "state = 'da_verificare' OR (verified_on IS NOT NULL AND evidence_reference IS NOT NULL AND length(trim(evidence_reference)) > 0)",
            name="ck_notice_recovery_proof",
        ),
        sa.CheckConstraint(
            "state NOT IN ('affidato', 'revocato', 'chiuso') OR (case_reference IS NOT NULL AND length(trim(case_reference)) > 0)",
            name="ck_notice_recovery_case",
        ),
        sa.CheckConstraint("amount IS NULL OR amount >= 0", name="ck_notice_recovery_amount"),
    )
    op.create_table(
        "ruolo_notice_audit", _id(), _document_id(),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("application_users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("before_json", sa.JSON(), nullable=False),
        sa.Column("after_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("document_id", "version", name="uq_notice_audit_version"),
        sa.CheckConstraint("length(trim(reason)) > 0", name="ck_notice_audit_reason"),
    )
    for table, columns in {
        "documents": ("document_number", "tax_code"),
        "positions": ("document_id", "avviso_id"),
        "attempts": ("document_id", "tracking_code"),
        "evidence": ("document_id",),
        "audit": ("document_id",),
    }.items():
        for column in columns:
            op.create_index(f"ix_ruolo_notice_{table}_{column}", f"ruolo_notice_{table}", [column])


def downgrade():
    for table in ("audit", "recoveries", "notifications", "evidence", "attempts", "positions", "documents"):
        op.drop_table(f"ruolo_notice_{table}")
