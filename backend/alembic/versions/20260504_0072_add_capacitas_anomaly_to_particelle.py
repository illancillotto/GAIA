"""capacitas: add anomaly fields to cat_particelle

Revision ID: 20260504_0072
Revises: 20260430_0071
Create Date: 2026-05-04 10:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260504_0072"
down_revision = "20260430_0071"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cat_particelle", sa.Column("capacitas_anomaly_type", sa.String(32), nullable=True))
    op.add_column("cat_particelle", sa.Column("capacitas_anomaly_data", sa.JSON(), nullable=True))
    op.create_index("ix_cat_particelle_capacitas_anomaly_type", "cat_particelle", ["capacitas_anomaly_type"])


def downgrade() -> None:
    op.drop_index("ix_cat_particelle_capacitas_anomaly_type", table_name="cat_particelle")
    op.drop_column("cat_particelle", "capacitas_anomaly_data")
    op.drop_column("cat_particelle", "capacitas_anomaly_type")
