"""Persist the selected postal slip layout, preserving v1 for existing rules."""

import sqlalchemy as sa

from alembic import op

revision = "20261026_0900"
down_revision = "20261023_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("bollettino_version", sa.String(2), nullable=False, server_default="v1"),
    )


def downgrade():
    op.drop_column("ruolo_tributi_calculation_policies", "bollettino_version")
