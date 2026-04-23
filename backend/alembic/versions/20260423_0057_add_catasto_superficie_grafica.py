"""add superficie_grafica_mq to catasto particelle tables

Revision ID: 20260423_0057
Revises: 20260422_0056
Create Date: 2026-04-23

"""

from __future__ import annotations

from typing import Union

import sqlalchemy as sa
from alembic import op

revision = "20260423_0057"
down_revision: Union[str, None] = "20260422_0056"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cat_particelle", sa.Column("superficie_grafica_mq", sa.Numeric(precision=12, scale=2), nullable=True))
    op.add_column(
        "cat_particelle_history",
        sa.Column("superficie_grafica_mq", sa.Numeric(precision=12, scale=2), nullable=True),
    )

    op.execute(
        """
        UPDATE cat_particelle
        SET superficie_grafica_mq = ROUND(ST_Area(ST_Transform(geometry, 3003))::numeric, 2)
        WHERE geometry IS NOT NULL
        """
    )
    op.execute(
        """
        UPDATE cat_particelle_history
        SET superficie_grafica_mq = ROUND(ST_Area(ST_Transform(geometry, 3003))::numeric, 2)
        WHERE geometry IS NOT NULL
        """
    )


def downgrade() -> None:
    op.drop_column("cat_particelle_history", "superficie_grafica_mq")
    op.drop_column("cat_particelle", "superficie_grafica_mq")
