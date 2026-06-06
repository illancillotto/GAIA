"""add application user login tracking fields

Revision ID: 20260606_0122
Revises: 20260606_0121
Create Date: 2026-06-06 16:10:00
"""

from alembic import op
import sqlalchemy as sa


revision = "20260606_0122"
down_revision = "20260606_0121"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application_users", sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("application_users", sa.Column("last_login_ip", sa.String(length=64), nullable=True))
    op.add_column("application_users", sa.Column("login_count", sa.Integer(), nullable=False, server_default="0"))


def downgrade() -> None:
    op.drop_column("application_users", "login_count")
    op.drop_column("application_users", "last_login_ip")
    op.drop_column("application_users", "last_login_at")
