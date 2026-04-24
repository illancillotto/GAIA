"""rename cat certificato intestatari

Revision ID: 20260424_0062
Revises: 20260424_0061
Create Date: 2026-04-24 11:35:00
"""

from collections.abc import Sequence

from alembic import op


revision: str = "20260424_0062"
down_revision: str | None = "20260424_0061"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.rename_table("cat_certificato_intestatari", "cat_capacitas_intestatari")
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_certificato_intestatari_certificato_id" '
        'RENAME TO "ix_cat_capacitas_intestatari_certificato_id"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_certificato_intestatari_subject_id" '
        'RENAME TO "ix_cat_capacitas_intestatari_subject_id"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_certificato_intestatari_idxana" '
        'RENAME TO "ix_cat_capacitas_intestatari_idxana"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_certificato_intestatari_idxesa" '
        'RENAME TO "ix_cat_capacitas_intestatari_idxesa"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_certificato_intestatari_codice_fiscale" '
        'RENAME TO "ix_cat_capacitas_intestatari_codice_fiscale"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_certificato_intestatari_comune_residenza" '
        'RENAME TO "ix_cat_capacitas_intestatari_comune_residenza"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_certificato_intestatari_collected_at" '
        'RENAME TO "ix_cat_capacitas_intestatari_collected_at"'
    )


def downgrade() -> None:
    op.rename_table("cat_capacitas_intestatari", "cat_certificato_intestatari")
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_capacitas_intestatari_certificato_id" '
        'RENAME TO "ix_cat_certificato_intestatari_certificato_id"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_capacitas_intestatari_subject_id" '
        'RENAME TO "ix_cat_certificato_intestatari_subject_id"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_capacitas_intestatari_idxana" '
        'RENAME TO "ix_cat_certificato_intestatari_idxana"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_capacitas_intestatari_idxesa" '
        'RENAME TO "ix_cat_certificato_intestatari_idxesa"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_capacitas_intestatari_codice_fiscale" '
        'RENAME TO "ix_cat_certificato_intestatari_codice_fiscale"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_capacitas_intestatari_comune_residenza" '
        'RENAME TO "ix_cat_certificato_intestatari_comune_residenza"'
    )
    op.execute(
        'ALTER INDEX IF EXISTS "ix_cat_capacitas_intestatari_collected_at" '
        'RENAME TO "ix_cat_certificato_intestatari_collected_at"'
    )
