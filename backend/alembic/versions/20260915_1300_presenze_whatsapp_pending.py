"""Persist pending reminder days and uncertain attempt references."""

import sqlalchemy as sa
from alembic import op

revision = "20260915_1300"
down_revision = "20260915_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presenze_whatsapp_receipts",
        sa.Column("provider_message_id", sa.String(255), primary_key=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "presenze_whatsapp_pending_days",
        sa.Column(
            "collaborator_id",
            sa.Uuid(),
            sa.ForeignKey("presenze_collaborators.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("work_date", sa.Date(), primary_key=True),
        sa.Column(
            "last_message_id",
            sa.Uuid(),
            sa.ForeignKey("presenze_whatsapp_messages.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_presenze_whatsapp_pending_days_last_message_id",
        "presenze_whatsapp_pending_days",
        ["last_message_id"],
    )


def downgrade() -> None:
    op.drop_table("presenze_whatsapp_pending_days")
    op.drop_table("presenze_whatsapp_receipts")
