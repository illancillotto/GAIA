"""Add configurable bollettino fields to Ruolo calculation policies.

Revision ID: 20260824_0900
Revises: 20260820_1100
"""

from alembic import op
import sqlalchemy as sa


revision = "20260824_0900"
down_revision = "20260820_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("bollettino_causale", sa.String(length=3), nullable=True),
    )
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("bollettino_esercizio", sa.String(length=4), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ruolo_tributi_calculation_policies", "bollettino_esercizio")
    op.drop_column("ruolo_tributi_calculation_policies", "bollettino_causale")
