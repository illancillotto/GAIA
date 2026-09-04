"""Normalize the legacy GATE team supervisor permission scope.

Revision ID: 20260904_1000
Revises: 20260902_1200
"""

from alembic import op

revision = "20260904_1000"
down_revision = "20260902_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE organization_team_supervisor_assignments
        SET permission_scope = 'manage_team'
        WHERE permission_scope = 'team'
        """
    )


def downgrade() -> None:
    # The original rows cannot be distinguished from canonical manage_team rows.
    pass
