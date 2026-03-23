"""application users

Revision ID: 20260320_0002
Revises: 20260319_0001
Create Date: 2026-03-20 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260320_0002"
down_revision = "20260319_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "application_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_application_users_id", "application_users", ["id"], unique=False)
    op.create_index("ix_application_users_username", "application_users", ["username"], unique=True)
    op.create_index("ix_application_users_email", "application_users", ["email"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_application_users_email", table_name="application_users")
    op.drop_index("ix_application_users_username", table_name="application_users")
    op.drop_index("ix_application_users_id", table_name="application_users")
    op.drop_table("application_users")
