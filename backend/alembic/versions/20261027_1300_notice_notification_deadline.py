"""Choose payment within sixty days of notification, preserving existing fixed dates."""

import sqlalchemy as sa
from alembic import op

revision = "20261027_1300"
down_revision = "20261027_1100"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("payment_deadline_mode", sa.String(32), nullable=False, server_default="fixed_date"),
    )


def downgrade():
    op.drop_column("ruolo_tributi_calculation_policies", "payment_deadline_mode")
