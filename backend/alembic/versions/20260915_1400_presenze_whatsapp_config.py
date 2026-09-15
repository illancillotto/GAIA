"""Persist encrypted WhatsApp runtime configuration."""

import sqlalchemy as sa

from alembic import op

revision = "20260915_1400"
down_revision = "20260915_1300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "presenze_whatsapp_config",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("provider", sa.String(16), nullable=False, server_default=""),
        sa.Column("waha_url", sa.String(500), nullable=False, server_default="http://waha:3000"),
        sa.Column("waha_session", sa.String(100), nullable=False, server_default="default"),
        sa.Column("waha_api_key_encrypted", sa.Text(), nullable=True),
        sa.Column("waha_hmac_key_encrypted", sa.Text(), nullable=True),
        sa.Column("reminder_cron", sa.String(100), nullable=False, server_default="30 9 * * 1-5"),
        sa.Column("lookback_days", sa.Integer(), nullable=False, server_default="3"),
        sa.Column(
            "include_missing_punches", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("max_per_run", sa.Integer(), nullable=False, server_default="40"),
        sa.Column("min_delay_seconds", sa.Integer(), nullable=False, server_default="25"),
        sa.Column("max_delay_seconds", sa.Integer(), nullable=False, server_default="75"),
        sa.Column("send_start_hour", sa.Integer(), nullable=False, server_default="8"),
        sa.Column("send_end_hour", sa.Integer(), nullable=False, server_default="19"),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_by_user_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.CheckConstraint("id = 1", name="ck_presenze_whatsapp_config_singleton"),
    )


def downgrade() -> None:
    op.drop_table("presenze_whatsapp_config")
