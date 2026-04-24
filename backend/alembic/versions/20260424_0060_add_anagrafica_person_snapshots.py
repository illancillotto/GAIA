"""add anagrafica person snapshots

Revision ID: 20260424_0060
Revises: 20260423_0059
Create Date: 2026-04-24 07:30:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260424_0060"
down_revision = "20260423_0059"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ana_person_snapshots",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=False),
        sa.Column("source_system", sa.String(length=32), nullable=False),
        sa.Column("source_ref", sa.String(length=128), nullable=True),
        sa.Column("cognome", sa.String(length=255), nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=False),
        sa.Column("data_nascita", sa.Date(), nullable=True),
        sa.Column("comune_nascita", sa.String(length=255), nullable=True),
        sa.Column("indirizzo", sa.String(length=255), nullable=True),
        sa.Column("comune_residenza", sa.String(length=255), nullable=True),
        sa.Column("cap", sa.String(length=16), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("telefono", sa.String(length=64), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("valid_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ana_person_snapshots_subject_id"), "ana_person_snapshots", ["subject_id"], unique=False)
    op.create_index(op.f("ix_ana_person_snapshots_source_system"), "ana_person_snapshots", ["source_system"], unique=False)
    op.create_index(op.f("ix_ana_person_snapshots_source_ref"), "ana_person_snapshots", ["source_ref"], unique=False)
    op.create_index(op.f("ix_ana_person_snapshots_cognome"), "ana_person_snapshots", ["cognome"], unique=False)
    op.create_index(op.f("ix_ana_person_snapshots_nome"), "ana_person_snapshots", ["nome"], unique=False)
    op.create_index(op.f("ix_ana_person_snapshots_codice_fiscale"), "ana_person_snapshots", ["codice_fiscale"], unique=False)
    op.create_index(op.f("ix_ana_person_snapshots_valid_from"), "ana_person_snapshots", ["valid_from"], unique=False)
    op.create_index(op.f("ix_ana_person_snapshots_collected_at"), "ana_person_snapshots", ["collected_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_ana_person_snapshots_collected_at"), table_name="ana_person_snapshots")
    op.drop_index(op.f("ix_ana_person_snapshots_valid_from"), table_name="ana_person_snapshots")
    op.drop_index(op.f("ix_ana_person_snapshots_codice_fiscale"), table_name="ana_person_snapshots")
    op.drop_index(op.f("ix_ana_person_snapshots_nome"), table_name="ana_person_snapshots")
    op.drop_index(op.f("ix_ana_person_snapshots_cognome"), table_name="ana_person_snapshots")
    op.drop_index(op.f("ix_ana_person_snapshots_source_ref"), table_name="ana_person_snapshots")
    op.drop_index(op.f("ix_ana_person_snapshots_source_system"), table_name="ana_person_snapshots")
    op.drop_index(op.f("ix_ana_person_snapshots_subject_id"), table_name="ana_person_snapshots")
    op.drop_table("ana_person_snapshots")
