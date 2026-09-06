"""Persist the first SISTER submission; unknown historical dates stay unknown."""

import sqlalchemy as sa

from alembic import op

revision = "20260905_1100"
down_revision = "20260905_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catasto_visure_requests",
        sa.Column("sister_first_submitted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("catasto_visure_requests", "sister_first_submitted_at")
