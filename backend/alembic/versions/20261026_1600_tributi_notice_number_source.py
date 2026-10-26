"""Let a rule keep the existing inCASS avviso number instead of a new GAIA number."""

import sqlalchemy as sa

from alembic import op

revision = "20261026_1600"
down_revision = "20261026_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "ruolo_tributi_calculation_policies",
        sa.Column("notice_number_source", sa.String(8), nullable=False, server_default="gaia"),
    )


def downgrade():
    op.drop_column("ruolo_tributi_calculation_policies", "notice_number_source")
