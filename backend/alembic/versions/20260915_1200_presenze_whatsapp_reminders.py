"""Add Presenze WhatsApp punch reminder outbox, notified days and opt-outs."""

import sqlalchemy as sa
from alembic import op

revision = "20260915_1200"
down_revision = "20260909_0900"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presenze_whatsapp_messages",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "collaborator_id",
            sa.Uuid(),
            sa.ForeignKey("presenze_collaborators.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "application_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("phone_e164", sa.String(length=20), nullable=False),
        sa.Column("text_body", sa.Text(), nullable=False),
        sa.Column("days_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("provider_message_id", sa.String(length=255), nullable=True, unique=True),
        sa.Column("error_code", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_presenze_whatsapp_messages_collaborator_id", "presenze_whatsapp_messages", ["collaborator_id"])
    op.create_index(
        "ix_presenze_whatsapp_messages_application_user_id", "presenze_whatsapp_messages", ["application_user_id"]
    )
    op.create_index("ix_presenze_whatsapp_messages_status", "presenze_whatsapp_messages", ["status"])

    op.create_table(
        "presenze_whatsapp_notified_days",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column(
            "collaborator_id",
            sa.Uuid(),
            sa.ForeignKey("presenze_collaborators.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("problem", sa.String(length=32), nullable=False),
        sa.Column(
            "message_id",
            sa.Uuid(),
            sa.ForeignKey("presenze_whatsapp_messages.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("kind", "collaborator_id", "work_date", name="uq_presenze_whatsapp_notified_day"),
    )
    op.create_index(
        "ix_presenze_whatsapp_notified_days_collaborator_id", "presenze_whatsapp_notified_days", ["collaborator_id"]
    )
    op.create_index("ix_presenze_whatsapp_notified_days_message_id", "presenze_whatsapp_notified_days", ["message_id"])

    op.create_table(
        "presenze_whatsapp_opt_outs",
        sa.Column(
            "application_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("phone_e164", sa.String(length=20), nullable=True),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("presenze_whatsapp_opt_outs")
    op.drop_index("ix_presenze_whatsapp_notified_days_message_id", table_name="presenze_whatsapp_notified_days")
    op.drop_index("ix_presenze_whatsapp_notified_days_collaborator_id", table_name="presenze_whatsapp_notified_days")
    op.drop_table("presenze_whatsapp_notified_days")
    op.drop_index("ix_presenze_whatsapp_messages_status", table_name="presenze_whatsapp_messages")
    op.drop_index("ix_presenze_whatsapp_messages_application_user_id", table_name="presenze_whatsapp_messages")
    op.drop_index("ix_presenze_whatsapp_messages_collaborator_id", table_name="presenze_whatsapp_messages")
    op.drop_table("presenze_whatsapp_messages")
