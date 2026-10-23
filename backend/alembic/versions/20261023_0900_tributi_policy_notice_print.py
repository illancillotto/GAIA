"""Let each annual calculation policy set the notice payment date and the TD 896 slip."""

import sqlalchemy as sa

from alembic import op

revision = "20261023_0900"
down_revision = "20261021_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("print_bollettino", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("payment_due_date", sa.Date(), nullable=True),
    )


def downgrade():
    op.drop_column("ruolo_tributi_calculation_policies", "payment_due_date")
    op.drop_column("ruolo_tributi_calculation_policies", "print_bollettino")
