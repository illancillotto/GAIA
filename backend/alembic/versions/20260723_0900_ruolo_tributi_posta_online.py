"""ruolo tributi posta online registered mails

Revision ID: 20260723_0900
Revises: 20260722_1500
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260723_0900"
down_revision = "20260722_1500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ruolo_tributi_posta_online_import_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_total", sa.Integer(), nullable=True),
        sa.Column("records_imported", sa.Integer(), nullable=True),
        sa.Column("records_matched", sa.Integer(), nullable=True),
        sa.Column("records_ambiguous", sa.Integer(), nullable=True),
        sa.Column("records_unmatched", sa.Integer(), nullable=True),
        sa.Column("records_errors", sa.Integer(), nullable=True),
        sa.Column("annualita_json", sa.JSON(), nullable=True),
        sa.Column("anomalies_json", sa.JSON(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("triggered_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["triggered_by"], ["application_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_posta_online_import_jobs_created_by", "ruolo_tributi_posta_online_import_jobs", ["triggered_by"])
    op.create_index("ix_ruolo_tributi_posta_online_import_jobs_source", "ruolo_tributi_posta_online_import_jobs", ["source"])
    op.create_index("ix_ruolo_tributi_posta_online_import_jobs_status", "ruolo_tributi_posta_online_import_jobs", ["status"])

    op.create_table(
        "ruolo_tributi_registered_mails",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=True),
        sa.Column("avviso_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("source_system", sa.String(length=40), nullable=False),
        sa.Column("source_shipment_id", sa.String(length=80), nullable=False),
        sa.Column("recipient_index", sa.Integer(), nullable=False),
        sa.Column("shipment_name", sa.String(length=300), nullable=True),
        sa.Column("service", sa.String(length=120), nullable=True),
        sa.Column("status_label", sa.String(length=120), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("recipient_name", sa.String(length=300), nullable=True),
        sa.Column("recipient_address", sa.Text(), nullable=True),
        sa.Column("recipient_city", sa.String(length=160), nullable=True),
        sa.Column("recipient_province", sa.String(length=16), nullable=True),
        sa.Column("recipient_zipcode", sa.String(length=16), nullable=True),
        sa.Column("tracking_number", sa.String(length=40), nullable=True),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("annualita_json", sa.JSON(), nullable=True),
        sa.Column("match_status", sa.String(length=24), nullable=False),
        sa.Column("match_score", sa.Integer(), nullable=True),
        sa.Column("match_reason", sa.Text(), nullable=True),
        sa.Column("anomaly_key", sa.String(length=80), nullable=True),
        sa.Column("recovery_status", sa.String(length=24), nullable=False),
        sa.Column("recovered_payment_id", sa.Uuid(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["avviso_id"], ["ruolo_avvisi.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["import_job_id"], ["ruolo_tributi_posta_online_import_jobs.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["recovered_payment_id"], ["ruolo_tributi_payments.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("source_system", "source_shipment_id", "recipient_index", name="uq_ruolo_tributi_registered_mail_source_recipient"),
    )
    op.create_index("ix_ruolo_tributi_registered_mails_anomaly_key", "ruolo_tributi_registered_mails", ["anomaly_key"])
    op.create_index("ix_ruolo_tributi_registered_mails_avviso_id", "ruolo_tributi_registered_mails", ["avviso_id"])
    op.create_index("ix_ruolo_tributi_registered_mails_created_at", "ruolo_tributi_registered_mails", ["created_at"])
    op.create_index("ix_ruolo_tributi_registered_mails_import_job_id", "ruolo_tributi_registered_mails", ["import_job_id"])
    op.create_index("ix_ruolo_tributi_registered_mails_match_status", "ruolo_tributi_registered_mails", ["match_status"])
    op.create_index("ix_ruolo_tributi_registered_mails_recipient_city", "ruolo_tributi_registered_mails", ["recipient_city"])
    op.create_index("ix_ruolo_tributi_registered_mails_recipient_name", "ruolo_tributi_registered_mails", ["recipient_name"])
    op.create_index("ix_ruolo_tributi_registered_mails_recovered_payment_id", "ruolo_tributi_registered_mails", ["recovered_payment_id"])
    op.create_index("ix_ruolo_tributi_registered_mails_recovery_status", "ruolo_tributi_registered_mails", ["recovery_status"])
    op.create_index("ix_ruolo_tributi_registered_mails_sent_at", "ruolo_tributi_registered_mails", ["sent_at"])
    op.create_index("ix_ruolo_tributi_registered_mails_source_shipment_id", "ruolo_tributi_registered_mails", ["source_shipment_id"])
    op.create_index("ix_ruolo_tributi_registered_mails_source_system", "ruolo_tributi_registered_mails", ["source_system"])
    op.create_index("ix_ruolo_tributi_registered_mails_status_label", "ruolo_tributi_registered_mails", ["status_label"])
    op.create_index("ix_ruolo_tributi_registered_mails_subject_id", "ruolo_tributi_registered_mails", ["subject_id"])
    op.create_index("ix_ruolo_tributi_registered_mails_tracking_number", "ruolo_tributi_registered_mails", ["tracking_number"])


def downgrade() -> None:
    op.drop_index("ix_ruolo_tributi_registered_mails_tracking_number", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_subject_id", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_status_label", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_source_system", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_source_shipment_id", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_sent_at", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_recovery_status", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_recovered_payment_id", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_recipient_name", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_recipient_city", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_match_status", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_import_job_id", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_created_at", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_avviso_id", table_name="ruolo_tributi_registered_mails")
    op.drop_index("ix_ruolo_tributi_registered_mails_anomaly_key", table_name="ruolo_tributi_registered_mails")
    op.drop_table("ruolo_tributi_registered_mails")

    op.drop_index("ix_ruolo_tributi_posta_online_import_jobs_status", table_name="ruolo_tributi_posta_online_import_jobs")
    op.drop_index("ix_ruolo_tributi_posta_online_import_jobs_source", table_name="ruolo_tributi_posta_online_import_jobs")
    op.drop_index("ix_ruolo_tributi_posta_online_import_jobs_created_by", table_name="ruolo_tributi_posta_online_import_jobs")
    op.drop_table("ruolo_tributi_posta_online_import_jobs")
