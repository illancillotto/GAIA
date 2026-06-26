"""rename application_users.module_inaz to module_presenze

Revision ID: 20260625_0900
Revises: 20260624_2100
Create Date: 2026-06-25
"""

from alembic import op
import sqlalchemy as sa


revision = "20260625_0900"
down_revision = "20260624_2100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("application_users", "module_inaz", new_column_name="module_presenze", existing_type=sa.Boolean())


def downgrade() -> None:
    op.alter_column("application_users", "module_presenze", new_column_name="module_inaz", existing_type=sa.Boolean())
