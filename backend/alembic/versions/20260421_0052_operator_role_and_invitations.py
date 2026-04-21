"""add operator role and operator_invitation table

Revision ID: 20260421_0052
Revises: 20260420_0051
Create Date: 2026-04-21
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260421_0052"
down_revision: Union[str, None] = "20260420_0051"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "operator_invitation",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("wc_operator_id", sa.Uuid(), nullable=False),
        sa.Column("token", sa.String(64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("activated_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["wc_operator_id"], ["wc_operator.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["application_users.id"]),
        sa.ForeignKeyConstraint(["activated_user_id"], ["application_users.id"]),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_operator_invitation_token", "operator_invitation", ["token"])
    op.create_index("ix_operator_invitation_wc_operator_id", "operator_invitation", ["wc_operator_id"])


def downgrade() -> None:
    op.drop_index("ix_operator_invitation_wc_operator_id", "operator_invitation")
    op.drop_index("ix_operator_invitation_token", "operator_invitation")
    op.drop_table("operator_invitation")
