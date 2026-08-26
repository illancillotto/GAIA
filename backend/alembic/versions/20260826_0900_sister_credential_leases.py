"""Prevent concurrent use of SISTER accounts across batches.

Revision ID: 20260826_0900
Revises: 20260825_1000
"""

from alembic import op
import sqlalchemy as sa

revision = "20260826_0900"
down_revision = "20260825_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catasto_credential_leases",
        sa.Column("sister_username", sa.String(length=128), nullable=False),
        sa.Column("credential_id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["credential_id"], ["catasto_credentials.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["catasto_batches.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("sister_username"),
    )
    op.create_index("ix_catasto_credential_leases_credential_id", "catasto_credential_leases", ["credential_id"])
    op.create_index("ix_catasto_credential_leases_batch_id", "catasto_credential_leases", ["batch_id"])
    op.create_index("ix_catasto_credential_leases_expires_at", "catasto_credential_leases", ["expires_at"])


def downgrade() -> None:
    op.drop_table("catasto_credential_leases")
