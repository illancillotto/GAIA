"""Add a credential allowlist to Catasto batches.

Revision ID: 20260827_1100
Revises: 20260827_1000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260827_1100"
down_revision = "20260827_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("catasto_batches", sa.Column("credential_ids", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("catasto_batches", "credential_ids")
