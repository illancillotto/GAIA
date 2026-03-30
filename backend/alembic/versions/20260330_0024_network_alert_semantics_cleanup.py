"""resolve legacy network alerts after semantic change

Revision ID: 20260330_0024
Revises: 20260330_0023
Create Date: 2026-03-30 16:35:00
"""

from alembic import op


revision = "20260330_0024"
down_revision = "20260330_0023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE network_alerts
        SET status = 'resolved',
            acknowledged_at = NOW()
        WHERE status = 'open'
          AND alert_type IN ('new_device', 'NEW_DEVICE', 'device_offline');
        """
    )


def downgrade() -> None:
    pass
