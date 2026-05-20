"""add external references to mobile sync events

Revision ID: 20260520_0088
Revises: 20260519_0087
Create Date: 2026-05-20
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260520_0088"
down_revision: Union[str, None] = "20260519_0087"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("mobile_sync_event", sa.Column("cloud_event_id", sa.Uuid(), nullable=True))
    op.add_column("mobile_sync_event", sa.Column("external_reference", sa.String(length=255), nullable=True))
    op.create_index("ix_mobile_sync_event_cloud_event_id", "mobile_sync_event", ["cloud_event_id"], unique=False)
    op.create_index("ix_mobile_sync_event_external_reference", "mobile_sync_event", ["external_reference"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mobile_sync_event_external_reference", table_name="mobile_sync_event")
    op.drop_index("ix_mobile_sync_event_cloud_event_id", table_name="mobile_sync_event")
    op.drop_column("mobile_sync_event", "external_reference")
    op.drop_column("mobile_sync_event", "cloud_event_id")
