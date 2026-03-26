"""catasto connection tests

Revision ID: 20260324_0010
Revises: 20260324_0009
Create Date: 2026-03-24 02:15:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0010"
down_revision = "20260324_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "catasto_connection_tests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("credential_id", sa.Uuid(), nullable=True),
        sa.Column("sister_username", sa.String(length=128), nullable=False),
        sa.Column("sister_password_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("ufficio_provinciale", sa.String(length=255), nullable=False, server_default="ORISTANO Territorio"),
        sa.Column("persist_verification", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("mode", sa.String(length=32), nullable=True),
        sa.Column("reachable", sa.Boolean(), nullable=True),
        sa.Column("authenticated", sa.Boolean(), nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["credential_id"], ["catasto_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catasto_connection_tests_user_id", "catasto_connection_tests", ["user_id"], unique=False)
    op.create_index("ix_catasto_connection_tests_status", "catasto_connection_tests", ["status"], unique=False)


def downgrade() -> None:
    op.drop_table("catasto_connection_tests")
