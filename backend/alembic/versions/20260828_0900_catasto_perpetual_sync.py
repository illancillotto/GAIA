"""add perpetual catasto synchronization planner

Revision ID: 20260828_0900
Revises: 20260827_1100
"""

import sqlalchemy as sa
from alembic import op

revision = "20260828_0900"
down_revision = "20260827_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for name, column in (
        ("credential_ids", sa.Column("credential_ids", sa.JSON(), nullable=True)),
        ("primary_enabled", sa.Column("primary_enabled", sa.Boolean(), nullable=False, server_default=sa.true())),
        ("secondary_enabled", sa.Column("secondary_enabled", sa.Boolean(), nullable=False, server_default=sa.false())),
        ("role_parcel_refresh_hours", sa.Column("role_parcel_refresh_hours", sa.Integer(), nullable=False, server_default="168")),
        ("role_subject_refresh_hours", sa.Column("role_subject_refresh_hours", sa.Integer(), nullable=False, server_default="168")),
        ("consortium_parcel_refresh_hours", sa.Column("consortium_parcel_refresh_hours", sa.Integer(), nullable=False, server_default="2160")),
        ("registry_subject_refresh_hours", sa.Column("registry_subject_refresh_hours", sa.Integer(), nullable=False, server_default="2160")),
        ("batch_size", sa.Column("batch_size", sa.Integer(), nullable=False, server_default="20")),
        ("source_watermarks", sa.Column("source_watermarks", sa.JSON(), nullable=True)),
        ("last_planner_at", sa.Column("last_planner_at", sa.DateTime(timezone=True), nullable=True)),
    ):
        op.add_column("catasto_ruolo_autosync_config", column)

    op.create_table(
        "catasto_perpetual_sync_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("scope", sa.String(40), nullable=False),
        sa.Column("target_key", sa.String(255), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("ruolo_particella_id", sa.Uuid(), nullable=True),
        sa.Column("cat_particella_id", sa.Uuid(), nullable=True),
        sa.Column("subject_id", sa.Uuid(), nullable=True),
        sa.Column("search_mode", sa.String(32), nullable=False),
        sa.Column("comune", sa.String(255), nullable=True),
        sa.Column("comune_codice", sa.String(255), nullable=True),
        sa.Column("catasto", sa.String(64), nullable=True),
        sa.Column("sezione", sa.String(64), nullable=True),
        sa.Column("foglio", sa.String(64), nullable=True),
        sa.Column("particella", sa.String(64), nullable=True),
        sa.Column("subalterno", sa.String(64), nullable=True),
        sa.Column("subject_kind", sa.String(16), nullable=True),
        sa.Column("subject_identifier", sa.String(64), nullable=True),
        sa.Column("intestazione", sa.String(255), nullable=True),
        sa.Column("tipo_visura", sa.String(64), nullable=False, server_default="Sintetica"),
        sa.Column("request_type", sa.String(32), nullable=False, server_default="ATTUALITA"),
        sa.Column("status", sa.String(32), nullable=False, server_default="pending"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_batch_id", sa.Uuid(), nullable=True),
        sa.Column("linked_request_id", sa.Uuid(), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_due_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("last_enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["ruolo_particella_id"], ["ruolo_particelle.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_batch_id"], ["catasto_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_request_id"], ["catasto_visure_requests.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "scope", "target_key", name="uq_catasto_perpetual_sync_target"),
    )
    for name, columns in (
        ("ix_catasto_perpetual_sync_items_user_id", ["user_id"]),
        ("ix_catasto_perpetual_sync_items_scope", ["scope"]),
        ("ix_catasto_perpetual_sync_items_priority", ["priority"]),
        ("ix_catasto_perpetual_sync_items_status", ["status"]),
        ("ix_catasto_perpetual_sync_items_ruolo_particella_id", ["ruolo_particella_id"]),
        ("ix_catasto_perpetual_sync_items_cat_particella_id", ["cat_particella_id"]),
        ("ix_catasto_perpetual_sync_items_subject_id", ["subject_id"]),
        ("ix_catasto_perpetual_sync_items_linked_batch_id", ["linked_batch_id"]),
        ("ix_catasto_perpetual_sync_items_linked_request_id", ["linked_request_id"]),
        ("ix_catasto_perpetual_sync_items_retry_after", ["retry_after"]),
        ("ix_catasto_perpetual_sync_items_next_due_at", ["next_due_at"]),
        ("ix_catasto_perpetual_sync_due", ["user_id", "status", "priority", "next_due_at"]),
    ):
        op.create_index(name, "catasto_perpetual_sync_items", columns)


def downgrade() -> None:
    op.drop_table("catasto_perpetual_sync_items")
    for name in (
        "last_planner_at", "source_watermarks", "batch_size",
        "registry_subject_refresh_hours", "consortium_parcel_refresh_hours",
        "role_subject_refresh_hours", "role_parcel_refresh_hours",
        "secondary_enabled", "primary_enabled", "credential_ids",
    ):
        op.drop_column("catasto_ruolo_autosync_config", name)
