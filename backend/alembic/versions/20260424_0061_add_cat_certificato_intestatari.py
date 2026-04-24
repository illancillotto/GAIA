"""add cat certificato intestatari

Revision ID: 20260424_0061
Revises: 20260424_0060
Create Date: 2026-04-24 10:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "20260424_0061"
down_revision: str | None = "20260424_0060"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cat_certificato_intestatari",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("certificato_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("subject_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("idxana", sa.String(length=64), nullable=True),
        sa.Column("idxesa", sa.String(length=64), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=32), nullable=True),
        sa.Column("denominazione", sa.String(length=500), nullable=True),
        sa.Column("data_nascita", sa.Date(), nullable=True),
        sa.Column("luogo_nascita", sa.String(length=255), nullable=True),
        sa.Column("residenza", sa.String(length=500), nullable=True),
        sa.Column("comune_residenza", sa.String(length=255), nullable=True),
        sa.Column("cap", sa.String(length=16), nullable=True),
        sa.Column("titoli", sa.String(length=255), nullable=True),
        sa.Column("deceduto", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("raw_payload_json", sa.JSON(), nullable=True),
        sa.Column("collected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["certificato_id"], ["cat_capacitas_certificati.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subject_id"], ["ana_subjects.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_cat_certificato_intestatari_certificato_id"),
        "cat_certificato_intestatari",
        ["certificato_id"],
        unique=False,
    )
    op.create_index(op.f("ix_cat_certificato_intestatari_subject_id"), "cat_certificato_intestatari", ["subject_id"], unique=False)
    op.create_index(op.f("ix_cat_certificato_intestatari_idxana"), "cat_certificato_intestatari", ["idxana"], unique=False)
    op.create_index(op.f("ix_cat_certificato_intestatari_idxesa"), "cat_certificato_intestatari", ["idxesa"], unique=False)
    op.create_index(
        op.f("ix_cat_certificato_intestatari_codice_fiscale"),
        "cat_certificato_intestatari",
        ["codice_fiscale"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_certificato_intestatari_comune_residenza"),
        "cat_certificato_intestatari",
        ["comune_residenza"],
        unique=False,
    )
    op.create_index(
        op.f("ix_cat_certificato_intestatari_collected_at"),
        "cat_certificato_intestatari",
        ["collected_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cat_certificato_intestatari_collected_at"), table_name="cat_certificato_intestatari")
    op.drop_index(op.f("ix_cat_certificato_intestatari_comune_residenza"), table_name="cat_certificato_intestatari")
    op.drop_index(op.f("ix_cat_certificato_intestatari_codice_fiscale"), table_name="cat_certificato_intestatari")
    op.drop_index(op.f("ix_cat_certificato_intestatari_idxesa"), table_name="cat_certificato_intestatari")
    op.drop_index(op.f("ix_cat_certificato_intestatari_idxana"), table_name="cat_certificato_intestatari")
    op.drop_index(op.f("ix_cat_certificato_intestatari_subject_id"), table_name="cat_certificato_intestatari")
    op.drop_index(op.f("ix_cat_certificato_intestatari_certificato_id"), table_name="cat_certificato_intestatari")
    op.drop_table("cat_certificato_intestatari")
