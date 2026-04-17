"""backfill ruolo module for existing admin users

Revision ID: 20260417_0049
Revises: 20260416_0048
Create Date: 2026-04-17
"""

from typing import Sequence, Union

from alembic import op


revision: str = "20260417_0049"
down_revision: Union[str, None] = "20260416_0048"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE application_users
        SET module_ruolo = TRUE
        WHERE role IN ('admin', 'super_admin')
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE application_users
        SET module_ruolo = FALSE
        WHERE role IN ('admin', 'super_admin')
        """
    )
