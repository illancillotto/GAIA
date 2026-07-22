"""ruolo tributi reminder batches

Revision ID: 20260722_1000
Revises: 20260717_1500
Create Date: 2026-07-22
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260722_1000"
down_revision = "20260717_1500"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ruolo_tributi_reminder_batches",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("title", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("template_path", sa.Text(), nullable=True),
        sa.Column("filters_json", sa.JSON(), nullable=True),
        sa.Column("items_total", sa.Integer(), nullable=False),
        sa.Column("items_generated", sa.Integer(), nullable=False),
        sa.Column("items_failed", sa.Integer(), nullable=False),
        sa.Column("generated_by", sa.Integer(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["generated_by"], ["application_users.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_reminder_batches_created_at", "ruolo_tributi_reminder_batches", ["created_at"])
    op.create_index("ix_ruolo_tributi_reminder_batches_generated_by", "ruolo_tributi_reminder_batches", ["generated_by"])
    op.create_index("ix_ruolo_tributi_reminder_batches_status", "ruolo_tributi_reminder_batches", ["status"])

    op.create_table(
        "ruolo_tributi_reminder_batch_items",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=300), nullable=True),
        sa.Column("comune_key", sa.String(length=120), nullable=True),
        sa.Column("years_json", sa.JSON(), nullable=True),
        sa.Column("avviso_ids_json", sa.JSON(), nullable=True),
        sa.Column("due_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("saldo_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("nas_folder_path", sa.Text(), nullable=True),
        sa.Column("generated_document_path", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["batch_id"], ["ruolo_tributi_reminder_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_ruolo_tributi_reminder_batch_items_batch_id", "ruolo_tributi_reminder_batch_items", ["batch_id"])
    op.create_index("ix_ruolo_tributi_reminder_batch_items_codice_fiscale", "ruolo_tributi_reminder_batch_items", ["codice_fiscale"])
    op.create_index("ix_ruolo_tributi_reminder_batch_items_comune_key", "ruolo_tributi_reminder_batch_items", ["comune_key"])
    op.create_index("ix_ruolo_tributi_reminder_batch_items_status", "ruolo_tributi_reminder_batch_items", ["status"])
    op.create_index("ix_ruolo_tributi_reminder_batch_items_subject_id", "ruolo_tributi_reminder_batch_items", ["subject_id"])


def downgrade() -> None:
    op.drop_index("ix_ruolo_tributi_reminder_batch_items_subject_id", table_name="ruolo_tributi_reminder_batch_items")
    op.drop_index("ix_ruolo_tributi_reminder_batch_items_status", table_name="ruolo_tributi_reminder_batch_items")
    op.drop_index("ix_ruolo_tributi_reminder_batch_items_comune_key", table_name="ruolo_tributi_reminder_batch_items")
    op.drop_index("ix_ruolo_tributi_reminder_batch_items_codice_fiscale", table_name="ruolo_tributi_reminder_batch_items")
    op.drop_index("ix_ruolo_tributi_reminder_batch_items_batch_id", table_name="ruolo_tributi_reminder_batch_items")
    op.drop_table("ruolo_tributi_reminder_batch_items")

    op.drop_index("ix_ruolo_tributi_reminder_batches_status", table_name="ruolo_tributi_reminder_batches")
    op.drop_index("ix_ruolo_tributi_reminder_batches_generated_by", table_name="ruolo_tributi_reminder_batches")
    op.drop_index("ix_ruolo_tributi_reminder_batches_created_at", table_name="ruolo_tributi_reminder_batches")
    op.drop_table("ruolo_tributi_reminder_batches")
