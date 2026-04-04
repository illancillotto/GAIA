"""sister multi credentials

Revision ID: 20260404_0029
Revises: 20260404_0028
Create Date: 2026-04-04 16:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260404_0029"
down_revision = "20260404_0028"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catasto_credentials",
        sa.Column("label", sa.String(length=255), nullable=False, server_default="SISTER"),
    )
    op.add_column(
        "catasto_credentials",
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.add_column(
        "catasto_credentials",
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )

    op.execute("UPDATE catasto_credentials SET label = sister_username WHERE label = 'SISTER'")
    op.execute("UPDATE catasto_credentials SET is_default = true")

    op.drop_constraint("uq_catasto_credentials_user_id", "catasto_credentials", type_="unique")
    op.create_unique_constraint(
        "uq_catasto_credentials_user_username",
        "catasto_credentials",
        ["user_id", "sister_username"],
    )

    op.alter_column("catasto_credentials", "label", server_default=None)
    op.alter_column("catasto_credentials", "active", server_default=None)
    op.alter_column("catasto_credentials", "is_default", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_catasto_credentials_user_username", "catasto_credentials", type_="unique")
    op.create_unique_constraint("uq_catasto_credentials_user_id", "catasto_credentials", ["user_id"])
    op.drop_column("catasto_credentials", "is_default")
    op.drop_column("catasto_credentials", "active")
    op.drop_column("catasto_credentials", "label")
