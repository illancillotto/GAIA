"""align presenze operai mpe threshold to three hours

Revision ID: 20260708_1030
Revises: 20260707_0800
Create Date: 2026-07-08 10:30:00
"""

from __future__ import annotations

from alembic import op


revision = "20260708_1030"
down_revision = "20260707_0800"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE presenze_operai_rule_configs
        SET mpe_review_threshold_minutes = 180
        WHERE code IN ('OPERAI_AGRARIO_1E3SAB', 'OPERAI_CATASTO_MAGAZZINO_ALTERNATI')
          AND mpe_review_threshold_minutes = 120
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE presenze_operai_rule_configs
        SET mpe_review_threshold_minutes = 120
        WHERE code IN ('OPERAI_AGRARIO_1E3SAB', 'OPERAI_CATASTO_MAGAZZINO_ALTERNATI')
          AND mpe_review_threshold_minutes = 180
        """
    )
