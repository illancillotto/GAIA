"""add cat utenza intestatari

Revision ID: 20260424_0063
Revises: 20260424_0062
Create Date: 2026-04-24 10:15:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "20260424_0063"
down_revision: str | None = "20260424_0062"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cat_utenza_intestatari",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("utenza_id", sa.Uuid(), nullable=False),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("idxana", sa.String(length=64), nullable=True),
        sa.Column("idxesa", sa.String(length=64), nullable=True),
        sa.Column("history_id", sa.String(length=64), nullable=True),
        sa.Column("anno_riferimento", sa.Integer(), nullable=True),
        sa.Column("data_agg", sa.DateTime(timezone=True), nullable=True),
        sa.Column("at", sa.String(length=10), nullable=True),
        sa.Column("site", sa.String(length=20), nullable=True),
        sa.Column("voltura", sa.String(length=20), nullable=True),
        sa.Column("op", sa.String(length=20), nullable=True),
        sa.Column("sn", sa.String(length=20), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=True),
        sa.Column("partita_iva", sa.String(length=32), nullable=True),
        sa.Column("denominazione", sa.String(length=500), nullable=True),
        sa.Column("data_nascita", sa.Date(), nullable=True),
        sa.Column("luogo_nascita", sa.String(length=255), nullable=True),
        sa.Column("sesso", sa.String(length=4), nullable=True),
        sa.Column("residenza", sa.String(length=500), nullable=True),
        sa.Column("comune_residenza", sa.String(length=255), nullable=True),
        sa.Column("cap", sa.String(length=16), nullable=True),
        sa.Column("titoli", sa.String(length=255), nullable=True),
        sa.Column("deceduto", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("raw_payload_json", postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["utenza_id"], ["cat_utenze_irrigue.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cat_utenza_intestatari_utenza_id"), "cat_utenza_intestatari", ["utenza_id"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_subject_id"), "cat_utenza_intestatari", ["subject_id"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_idxana"), "cat_utenza_intestatari", ["idxana"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_idxesa"), "cat_utenza_intestatari", ["idxesa"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_history_id"), "cat_utenza_intestatari", ["history_id"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_anno_riferimento"), "cat_utenza_intestatari", ["anno_riferimento"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_data_agg"), "cat_utenza_intestatari", ["data_agg"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_codice_fiscale"), "cat_utenza_intestatari", ["codice_fiscale"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_partita_iva"), "cat_utenza_intestatari", ["partita_iva"], unique=False)
    op.create_index(op.f("ix_cat_utenza_intestatari_collected_at"), "cat_utenza_intestatari", ["collected_at"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_cat_utenza_intestatari_collected_at"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_partita_iva"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_codice_fiscale"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_data_agg"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_anno_riferimento"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_history_id"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_idxesa"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_idxana"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_subject_id"), table_name="cat_utenza_intestatari")
    op.drop_index(op.f("ix_cat_utenza_intestatari_utenza_id"), table_name="cat_utenza_intestatari")
    op.drop_table("cat_utenza_intestatari")
