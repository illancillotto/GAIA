"""ruolo tributi special notices

Revision ID: 20260807_1200
Revises: 20260730_1100
Create Date: 2026-08-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260807_1200"
down_revision = "20260730_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ruolo_tributi_special_notices",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("payment_notice_id", sa.Uuid(), nullable=False),
        sa.Column("source_notice_id", sa.String(length=128), nullable=False),
        sa.Column("codice_ruolo", sa.String(length=16), nullable=False),
        sa.Column("kind", sa.String(length=40), nullable=False),
        sa.Column("label", sa.String(length=160), nullable=False),
        sa.Column("issue_year", sa.Integer(), nullable=True),
        sa.Column("reference_year", sa.Integer(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("identifier", sa.String(length=32), nullable=True),
        sa.Column("display_name", sa.String(length=512), nullable=True),
        sa.Column("default_tribute_code", sa.String(length=16), nullable=True),
        sa.Column("reconstruction_status", sa.String(length=32), nullable=False),
        sa.Column("allocation_status", sa.String(length=32), nullable=False),
        sa.Column("importo_carico", sa.Numeric(12, 2), nullable=True),
        sa.Column("importo_riscosso_abs", sa.Numeric(12, 2), nullable=True),
        sa.Column("importo_residuo", sa.Numeric(12, 2), nullable=True),
        sa.Column("allocated_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("paid_allocation_delta", sa.Numeric(12, 2), nullable=True),
        sa.Column("due_allocation_delta", sa.Numeric(12, 2), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["payment_notice_id"], ["ana_payment_notices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("payment_notice_id", name="uq_ruolo_tributi_special_notice_payment_notice"),
    )
    op.create_index("ix_ruolo_tributi_special_notices_payment_notice_id", "ruolo_tributi_special_notices", ["payment_notice_id"])
    op.create_index("ix_ruolo_tributi_special_notices_source_notice_id", "ruolo_tributi_special_notices", ["source_notice_id"])
    op.create_index("ix_ruolo_tributi_special_notices_codice_ruolo", "ruolo_tributi_special_notices", ["codice_ruolo"])
    op.create_index("ix_ruolo_tributi_special_notices_kind", "ruolo_tributi_special_notices", ["kind"])
    op.create_index("ix_ruolo_tributi_special_notices_issue_year", "ruolo_tributi_special_notices", ["issue_year"])
    op.create_index("ix_ruolo_tributi_special_notices_reference_year", "ruolo_tributi_special_notices", ["reference_year"])
    op.create_index("ix_ruolo_tributi_special_notices_subject_id", "ruolo_tributi_special_notices", ["subject_id"])
    op.create_index("ix_ruolo_tributi_special_notices_identifier", "ruolo_tributi_special_notices", ["identifier"])
    op.create_index("ix_ruolo_tributi_special_notices_display_name", "ruolo_tributi_special_notices", ["display_name"])
    op.create_index("ix_ruolo_tributi_special_notices_default_tribute_code", "ruolo_tributi_special_notices", ["default_tribute_code"])
    op.create_index("ix_ruolo_tributi_special_notices_reconstruction_status", "ruolo_tributi_special_notices", ["reconstruction_status"])
    op.create_index("ix_ruolo_tributi_special_notices_allocation_status", "ruolo_tributi_special_notices", ["allocation_status"])

    op.create_table(
        "ruolo_tributi_special_allocations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("special_notice_id", sa.Uuid(), nullable=False),
        sa.Column("target_avviso_id", sa.Uuid(), nullable=True),
        sa.Column("target_partita_id", sa.Uuid(), nullable=True),
        sa.Column("target_particella_id", sa.Uuid(), nullable=True),
        sa.Column("target_subject_id", sa.Uuid(), nullable=True),
        sa.Column("target_year", sa.Integer(), nullable=True),
        sa.Column("tribute_code", sa.String(length=16), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("allocation_mode", sa.String(length=24), nullable=False),
        sa.Column("reason", sa.String(length=160), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("voided_by", sa.Integer(), nullable=True),
        sa.Column("voided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["special_notice_id"], ["ruolo_tributi_special_notices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["target_avviso_id"], ["ruolo_avvisi.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_particella_id"], ["ruolo_particelle.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_partita_id"], ["ruolo_partite.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["voided_by"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_ruolo_tributi_special_allocations_special_notice_id", "ruolo_tributi_special_allocations", ["special_notice_id"])
    op.create_index("ix_ruolo_tributi_special_allocations_target_avviso_id", "ruolo_tributi_special_allocations", ["target_avviso_id"])
    op.create_index("ix_ruolo_tributi_special_allocations_target_partita_id", "ruolo_tributi_special_allocations", ["target_partita_id"])
    op.create_index("ix_ruolo_tributi_special_allocations_target_particella_id", "ruolo_tributi_special_allocations", ["target_particella_id"])
    op.create_index("ix_ruolo_tributi_special_allocations_target_subject_id", "ruolo_tributi_special_allocations", ["target_subject_id"])
    op.create_index("ix_ruolo_tributi_special_allocations_target_year", "ruolo_tributi_special_allocations", ["target_year"])
    op.create_index("ix_ruolo_tributi_special_allocations_tribute_code", "ruolo_tributi_special_allocations", ["tribute_code"])
    op.create_index("ix_ruolo_tributi_special_allocations_status", "ruolo_tributi_special_allocations", ["status"])
    op.create_index("ix_ruolo_tributi_special_allocations_allocation_mode", "ruolo_tributi_special_allocations", ["allocation_mode"])
    op.create_index("ix_ruolo_tributi_special_allocations_created_by", "ruolo_tributi_special_allocations", ["created_by"])
    op.create_index("ix_ruolo_tributi_special_allocations_voided_by", "ruolo_tributi_special_allocations", ["voided_by"])
    op.create_index("ix_ruolo_tributi_special_allocations_voided_at", "ruolo_tributi_special_allocations", ["voided_at"])


def downgrade() -> None:
    op.drop_index("ix_ruolo_tributi_special_allocations_voided_at", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_voided_by", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_created_by", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_allocation_mode", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_status", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_tribute_code", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_target_year", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_target_subject_id", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_target_particella_id", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_target_partita_id", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_target_avviso_id", table_name="ruolo_tributi_special_allocations")
    op.drop_index("ix_ruolo_tributi_special_allocations_special_notice_id", table_name="ruolo_tributi_special_allocations")
    op.drop_table("ruolo_tributi_special_allocations")

    op.drop_index("ix_ruolo_tributi_special_notices_allocation_status", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_reconstruction_status", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_default_tribute_code", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_display_name", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_identifier", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_subject_id", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_reference_year", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_issue_year", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_kind", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_codice_ruolo", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_source_notice_id", table_name="ruolo_tributi_special_notices")
    op.drop_index("ix_ruolo_tributi_special_notices_payment_notice_id", table_name="ruolo_tributi_special_notices")
    op.drop_table("ruolo_tributi_special_notices")
