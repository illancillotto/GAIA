"""inaz credentials user bound

Revision ID: 20260529_0101
Revises: 20260529_0100
Create Date: 2026-05-29
"""

from alembic import op
import sqlalchemy as sa


revision = "20260529_0101"
down_revision = "20260529_0100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("inaz_credentials", sa.Column("application_user_id", sa.Integer(), nullable=True))
    op.execute(
        """
        UPDATE inaz_credentials
        SET application_user_id = (
            SELECT id
            FROM application_users
            WHERE role IN ('admin', 'super_admin')
            ORDER BY id ASC
            LIMIT 1
        )
        """
    )
    op.alter_column("inaz_credentials", "application_user_id", nullable=False)
    op.create_foreign_key(
        "fk_inaz_credentials_application_user_id_application_users",
        "inaz_credentials",
        "application_users",
        ["application_user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_index(op.f("ix_inaz_credentials_application_user_id"), "inaz_credentials", ["application_user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_inaz_credentials_application_user_id"), table_name="inaz_credentials")
    op.drop_constraint("fk_inaz_credentials_application_user_id_application_users", "inaz_credentials", type_="foreignkey")
    op.drop_column("inaz_credentials", "application_user_id")
