"""allow generic project meter readings without distretto

Revision ID: 20260518_0086
Revises: 20260518_0085
Create Date: 2026-05-18 18:35:00.000000
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "20260518_0086"
down_revision = "20260518_0085"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("catasto_meter_reading_imports", "distretto_id", existing_type=sa.UUID(), nullable=True)
    op.alter_column("catasto_meter_readings", "distretto_id", existing_type=sa.UUID(), nullable=True)


def downgrade() -> None:
    op.alter_column("catasto_meter_readings", "distretto_id", existing_type=sa.UUID(), nullable=False)
    op.alter_column("catasto_meter_reading_imports", "distretto_id", existing_type=sa.UUID(), nullable=False)
