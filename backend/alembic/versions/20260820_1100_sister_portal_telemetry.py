"""Add structured SISTER portal telemetry events.

Revision ID: 20260820_1100
Revises: 20260820_1000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260820_1100"
down_revision = "20260820_1000"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sister_portal_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("batch_id", sa.Uuid(), nullable=True),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("credential_id", sa.Uuid(), nullable=True),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("run_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("step", sa.String(length=64), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("http_status", sa.Integer(), nullable=True),
        sa.Column("endpoint", sa.String(length=255), nullable=True),
        sa.Column("attempt", sa.Integer(), nullable=True),
        sa.Column("cooldown_seconds", sa.Integer(), nullable=True),
        sa.Column("context_json", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["batch_id"], ["catasto_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["request_id"], ["catasto_visure_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["credential_id"], ["catasto_credentials.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sister_portal_events_occurred_at", "sister_portal_events", ["occurred_at"])
    op.create_index(
        "ix_sister_portal_events_user_occurred",
        "sister_portal_events",
        ["user_id", "occurred_at"],
    )
    op.create_index(
        "ix_sister_portal_events_credential_occurred",
        "sister_portal_events",
        ["credential_id", "occurred_at"],
    )
    op.create_index(
        "ix_sister_portal_events_type_occurred",
        "sister_portal_events",
        ["event_type", "occurred_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_sister_portal_events_type_occurred", table_name="sister_portal_events")
    op.drop_index("ix_sister_portal_events_credential_occurred", table_name="sister_portal_events")
    op.drop_index("ix_sister_portal_events_user_occurred", table_name="sister_portal_events")
    op.drop_index("ix_sister_portal_events_occurred_at", table_name="sister_portal_events")
    op.drop_table("sister_portal_events")
