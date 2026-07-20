"""ruolo tributi payments and reminders

Revision ID: 20260717_1500
Revises: 20260717_0900
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260717_1500"
down_revision = "20260717_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ruolo_tributi_payment_import_jobs",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("filename", sa.String(length=300), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("records_total", sa.Integer(), nullable=True),
        sa.Column("records_imported", sa.Integer(), nullable=True),
        sa.Column("records_matched", sa.Integer(), nullable=True),
        sa.Column("records_unmatched", sa.Integer(), nullable=True),
        sa.Column("records_errors", sa.Integer(), nullable=True),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("mapping_json", sa.JSON(), nullable=True),
        sa.Column("triggered_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["triggered_by"], ["application_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_payment_import_jobs_source", "ruolo_tributi_payment_import_jobs", ["source"])
    op.create_index("ix_ruolo_tributi_payment_import_jobs_status", "ruolo_tributi_payment_import_jobs", ["status"])
    op.create_index(
        "ix_ruolo_tributi_payment_import_jobs_triggered_by",
        "ruolo_tributi_payment_import_jobs",
        ["triggered_by"],
    )

    op.create_table(
        "ruolo_tributi_payments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("avviso_id", sa.Uuid(), nullable=False),
        sa.Column("import_job_id", sa.Uuid(), nullable=True),
        sa.Column("codice_cnc_raw", sa.String(length=80), nullable=True),
        sa.Column("codice_utenza_raw", sa.String(length=80), nullable=True),
        sa.Column("anno_tributario", sa.Integer(), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_reference", sa.String(length=160), nullable=True),
        sa.Column("payment_method", sa.String(length=80), nullable=True),
        sa.Column("source", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["avviso_id"], ["ruolo_avvisi.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["import_job_id"], ["ruolo_tributi_payment_import_jobs.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("source", "payment_reference", name="uq_ruolo_tributi_payment_source_reference"),
    )
    op.create_index("ix_ruolo_tributi_payments_anno_tributario", "ruolo_tributi_payments", ["anno_tributario"])
    op.create_index("ix_ruolo_tributi_payments_avviso_id", "ruolo_tributi_payments", ["avviso_id"])
    op.create_index("ix_ruolo_tributi_payments_codice_cnc_raw", "ruolo_tributi_payments", ["codice_cnc_raw"])
    op.create_index("ix_ruolo_tributi_payments_codice_utenza_raw", "ruolo_tributi_payments", ["codice_utenza_raw"])
    op.create_index("ix_ruolo_tributi_payments_created_by", "ruolo_tributi_payments", ["created_by"])
    op.create_index("ix_ruolo_tributi_payments_import_job_id", "ruolo_tributi_payments", ["import_job_id"])
    op.create_index("ix_ruolo_tributi_payments_paid_at", "ruolo_tributi_payments", ["paid_at"])
    op.create_index("ix_ruolo_tributi_payments_payment_reference", "ruolo_tributi_payments", ["payment_reference"])
    op.create_index("ix_ruolo_tributi_payments_source", "ruolo_tributi_payments", ["source"])
    op.create_index("ix_ruolo_tributi_payments_status", "ruolo_tributi_payments", ["status"])

    op.create_table(
        "ruolo_tributi_avviso_status",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("avviso_id", sa.Uuid(), nullable=False),
        sa.Column("payment_status", sa.String(length=24), nullable=False),
        sa.Column("workflow_status", sa.String(length=24), nullable=True),
        sa.Column("saldo_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("last_payment_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("capacitas_url", sa.Text(), nullable=True),
        sa.Column("capacitas_avviso_code", sa.String(length=80), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["avviso_id"], ["ruolo_avvisi.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["updated_by"], ["application_users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("avviso_id"),
    )
    op.create_index("ix_ruolo_tributi_avviso_status_avviso_id", "ruolo_tributi_avviso_status", ["avviso_id"])
    op.create_index(
        "ix_ruolo_tributi_avviso_status_capacitas_avviso_code",
        "ruolo_tributi_avviso_status",
        ["capacitas_avviso_code"],
    )
    op.create_index("ix_ruolo_tributi_avviso_status_payment_status", "ruolo_tributi_avviso_status", ["payment_status"])
    op.create_index("ix_ruolo_tributi_avviso_status_updated_by", "ruolo_tributi_avviso_status", ["updated_by"])
    op.create_index("ix_ruolo_tributi_avviso_status_workflow_status", "ruolo_tributi_avviso_status", ["workflow_status"])

    op.create_table(
        "ruolo_tributi_notes",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("avviso_id", sa.Uuid(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("visibility", sa.String(length=24), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["avviso_id"], ["ruolo_avvisi.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["application_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_notes_avviso_id", "ruolo_tributi_notes", ["avviso_id"])
    op.create_index("ix_ruolo_tributi_notes_created_at", "ruolo_tributi_notes", ["created_at"])
    op.create_index("ix_ruolo_tributi_notes_created_by", "ruolo_tributi_notes", ["created_by"])
    op.create_index("ix_ruolo_tributi_notes_visibility", "ruolo_tributi_notes", ["visibility"])

    op.create_table(
        "ruolo_tributi_templates",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=160), nullable=False),
        sa.Column("template_path", sa.Text(), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["application_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_templates_created_by", "ruolo_tributi_templates", ["created_by"])
    op.create_index("ix_ruolo_tributi_templates_is_active", "ruolo_tributi_templates", ["is_active"])

    op.create_table(
        "ruolo_tributi_reminders",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("avviso_id", sa.Uuid(), nullable=False),
        sa.Column("template_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("generated_document_path", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("generated_by", sa.Integer(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["avviso_id"], ["ruolo_avvisi.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["generated_by"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["template_id"], ["ruolo_tributi_templates.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_reminders_avviso_id", "ruolo_tributi_reminders", ["avviso_id"])
    op.create_index("ix_ruolo_tributi_reminders_generated_by", "ruolo_tributi_reminders", ["generated_by"])
    op.create_index("ix_ruolo_tributi_reminders_status", "ruolo_tributi_reminders", ["status"])
    op.create_index("ix_ruolo_tributi_reminders_template_id", "ruolo_tributi_reminders", ["template_id"])


def downgrade() -> None:
    op.drop_index("ix_ruolo_tributi_reminders_template_id", table_name="ruolo_tributi_reminders")
    op.drop_index("ix_ruolo_tributi_reminders_status", table_name="ruolo_tributi_reminders")
    op.drop_index("ix_ruolo_tributi_reminders_generated_by", table_name="ruolo_tributi_reminders")
    op.drop_index("ix_ruolo_tributi_reminders_avviso_id", table_name="ruolo_tributi_reminders")
    op.drop_table("ruolo_tributi_reminders")

    op.drop_index("ix_ruolo_tributi_templates_is_active", table_name="ruolo_tributi_templates")
    op.drop_index("ix_ruolo_tributi_templates_created_by", table_name="ruolo_tributi_templates")
    op.drop_table("ruolo_tributi_templates")

    op.drop_index("ix_ruolo_tributi_notes_visibility", table_name="ruolo_tributi_notes")
    op.drop_index("ix_ruolo_tributi_notes_created_by", table_name="ruolo_tributi_notes")
    op.drop_index("ix_ruolo_tributi_notes_created_at", table_name="ruolo_tributi_notes")
    op.drop_index("ix_ruolo_tributi_notes_avviso_id", table_name="ruolo_tributi_notes")
    op.drop_table("ruolo_tributi_notes")

    op.drop_index("ix_ruolo_tributi_avviso_status_workflow_status", table_name="ruolo_tributi_avviso_status")
    op.drop_index("ix_ruolo_tributi_avviso_status_updated_by", table_name="ruolo_tributi_avviso_status")
    op.drop_index("ix_ruolo_tributi_avviso_status_payment_status", table_name="ruolo_tributi_avviso_status")
    op.drop_index("ix_ruolo_tributi_avviso_status_capacitas_avviso_code", table_name="ruolo_tributi_avviso_status")
    op.drop_index("ix_ruolo_tributi_avviso_status_avviso_id", table_name="ruolo_tributi_avviso_status")
    op.drop_table("ruolo_tributi_avviso_status")

    op.drop_index("ix_ruolo_tributi_payments_status", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_source", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_payment_reference", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_paid_at", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_import_job_id", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_created_by", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_codice_utenza_raw", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_codice_cnc_raw", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_avviso_id", table_name="ruolo_tributi_payments")
    op.drop_index("ix_ruolo_tributi_payments_anno_tributario", table_name="ruolo_tributi_payments")
    op.drop_table("ruolo_tributi_payments")

    op.drop_index("ix_ruolo_tributi_payment_import_jobs_triggered_by", table_name="ruolo_tributi_payment_import_jobs")
    op.drop_index("ix_ruolo_tributi_payment_import_jobs_status", table_name="ruolo_tributi_payment_import_jobs")
    op.drop_index("ix_ruolo_tributi_payment_import_jobs_source", table_name="ruolo_tributi_payment_import_jobs")
    op.drop_table("ruolo_tributi_payment_import_jobs")
