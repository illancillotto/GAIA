"""add network device lifecycle state

Revision ID: 20260604_0112
Revises: 20260604_0111
Create Date: 2026-06-04 13:20:00
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "20260604_0112"
down_revision: str | Sequence[str] | None = "20260604_0111"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "network_devices",
        sa.Column("lifecycle_state", sa.String(length=32), nullable=False, server_default="active"),
    )
    op.add_column("network_devices", sa.Column("retired_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(op.f("ix_network_devices_lifecycle_state"), "network_devices", ["lifecycle_state"], unique=False)
    op.execute("UPDATE network_devices SET lifecycle_state = 'active' WHERE lifecycle_state IS NULL")
    op.alter_column("network_devices", "lifecycle_state", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_network_devices_lifecycle_state"), table_name="network_devices")
    op.drop_column("network_devices", "retired_at")
    op.drop_column("network_devices", "lifecycle_state")
