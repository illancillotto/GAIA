"""Classify explicitly named organizational departments as reparto units.

Revision ID: 20260826_1000
Revises: 20260825_1300
"""

from alembic import op


revision = "20260826_1000"
down_revision = "20260825_1300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE org_unit
        SET tipo = 'reparto'
        WHERE structure_kind = 'organigramma'
          AND tipo = 'settore'
          AND lower(btrim(nome)) LIKE 'reparto %'
        """
    )
    op.execute(
        """
        UPDATE org_revision_unit
        SET tipo = 'reparto'
        WHERE tipo = 'settore'
          AND lower(btrim(nome)) LIKE 'reparto %'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE org_revision_unit
        SET tipo = 'settore'
        WHERE tipo = 'reparto'
          AND lower(btrim(nome)) LIKE 'reparto %'
        """
    )
    op.execute(
        """
        UPDATE org_unit
        SET tipo = 'settore'
        WHERE structure_kind = 'organigramma'
          AND tipo = 'reparto'
          AND lower(btrim(nome)) LIKE 'reparto %'
        """
    )
