"""add mobile sync event table for gaia mobile integration

Revision ID: 20260519_0087
Revises: 20260518_0086
Create Date: 2026-05-19
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260519_0087"
down_revision: Union[str, None] = "20260518_0086"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "mobile_sync_event",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("client_event_id", sa.Uuid(), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("operator_id", sa.Uuid(), nullable=False),
        sa.Column("device_id", sa.String(length=128), nullable=False),
        sa.Column("payload_version", sa.Integer(), nullable=False),
        sa.Column("payload_hash", sa.String(length=128), nullable=False),
        sa.Column("gaia_entity_type", sa.String(length=64), nullable=False),
        sa.Column("gaia_entity_id", sa.String(length=128), nullable=False),
        sa.Column("source_entity_id", sa.Uuid(), nullable=True),
        sa.Column("payload_json", sa.JSON(), nullable=True),
        sa.Column("result_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["operator_id"], ["wc_operator.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("client_event_id"),
    )
    op.create_index("ix_mobile_sync_event_client_event_id", "mobile_sync_event", ["client_event_id"], unique=True)
    op.create_index("ix_mobile_sync_event_device_id", "mobile_sync_event", ["device_id"], unique=False)
    op.create_index("ix_mobile_sync_event_event_type", "mobile_sync_event", ["event_type"], unique=False)
    op.create_index("ix_mobile_sync_event_gaia_entity_id", "mobile_sync_event", ["gaia_entity_id"], unique=False)
    op.create_index("ix_mobile_sync_event_gaia_entity_type", "mobile_sync_event", ["gaia_entity_type"], unique=False)
    op.create_index("ix_mobile_sync_event_operator_id", "mobile_sync_event", ["operator_id"], unique=False)
    op.create_index("ix_mobile_sync_event_source_entity_id", "mobile_sync_event", ["source_entity_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_mobile_sync_event_source_entity_id", table_name="mobile_sync_event")
    op.drop_index("ix_mobile_sync_event_operator_id", table_name="mobile_sync_event")
    op.drop_index("ix_mobile_sync_event_gaia_entity_type", table_name="mobile_sync_event")
    op.drop_index("ix_mobile_sync_event_gaia_entity_id", table_name="mobile_sync_event")
    op.drop_index("ix_mobile_sync_event_event_type", table_name="mobile_sync_event")
    op.drop_index("ix_mobile_sync_event_device_id", table_name="mobile_sync_event")
    op.drop_index("ix_mobile_sync_event_client_event_id", table_name="mobile_sync_event")
    op.drop_table("mobile_sync_event")
