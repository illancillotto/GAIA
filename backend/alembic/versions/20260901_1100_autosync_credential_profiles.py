"""add AutoSync-specific credential profiles

Revision ID: 20260901_1100
Revises: 20260901_1000
"""

import sqlalchemy as sa
from alembic import op

revision = "20260901_1100"
down_revision = "20260901_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "catasto_ruolo_autosync_config",
        sa.Column("credential_profiles", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("catasto_ruolo_autosync_config", "credential_profiles")
