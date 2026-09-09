"""Raise the standard Presenze MPE review threshold to five hours."""

from alembic import op

revision = "20260909_0900"
down_revision = "20260905_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE presenze_operai_rule_configs
        SET mpe_review_threshold_minutes = 300
        WHERE code IN ('OPERAI_AGRARIO_1E3SAB', 'OPERAI_CATASTO_MAGAZZINO_ALTERNATI')
          AND mpe_review_threshold_minutes IN (120, 180)
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE presenze_operai_rule_configs
        SET mpe_review_threshold_minutes = 180
        WHERE code IN ('OPERAI_AGRARIO_1E3SAB', 'OPERAI_CATASTO_MAGAZZINO_ALTERNATI')
          AND mpe_review_threshold_minutes = 300
        """
    )
