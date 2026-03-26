"""share parent_id

Revision ID: 20260323_0007
Revises: 20260323_0006
Create Date: 2026-03-23 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260323_0007"
down_revision = "20260323_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("shares", sa.Column("parent_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_shares_parent_id",
        "shares",
        "shares",
        ["parent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_shares_parent_id", "shares", ["parent_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_shares_parent_id", table_name="shares")
    op.drop_constraint("fk_shares_parent_id", "shares", type_="foreignkey")
    op.drop_column("shares", "parent_id")
