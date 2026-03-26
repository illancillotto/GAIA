"""add module flags to application_users

Revision ID: 20260324_0011
Revises: 20260324_0010
Create Date: 2026-03-24
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0011"
down_revision = "20260324_0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("application_users", sa.Column("module_accessi", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.add_column("application_users", sa.Column("module_rete", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("application_users", sa.Column("module_inventario", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.alter_column("application_users", "module_accessi", server_default=None)
    op.alter_column("application_users", "module_rete", server_default=None)
    op.alter_column("application_users", "module_inventario", server_default=None)


def downgrade() -> None:
    op.drop_column("application_users", "module_inventario")
    op.drop_column("application_users", "module_rete")
    op.drop_column("application_users", "module_accessi")
