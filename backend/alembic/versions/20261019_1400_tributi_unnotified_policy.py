"""Restrict annual calculation policies to undocumented notifications on request."""

import sqlalchemy as sa

from alembic import op

revision = "20261019_1400"
down_revision = "20261005_1500"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("only_unnotified", sa.Boolean(), nullable=False, server_default=sa.false()),
    )


def downgrade():
    op.drop_column("ruolo_tributi_calculation_policies", "only_unnotified")
