"""Allow ongoing shift assignments without inventing an expiry date."""

import sqlalchemy as sa

from alembic import op

revision = "20261005_1500"
down_revision = "20261003_1200"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("presenze_shift_assignments") as batch:
        batch.alter_column("date_to", existing_type=sa.Date(), nullable=True)


def downgrade():
    count = (
        op.get_bind()
        .execute(sa.text("SELECT count(*) FROM presenze_shift_assignments WHERE date_to IS NULL"))
        .scalar_one()
    )
    if count:
        raise RuntimeError("Close ongoing shift assignments explicitly before downgrade")
    with op.batch_alter_table("presenze_shift_assignments") as batch:
        batch.alter_column("date_to", existing_type=sa.Date(), nullable=False)
