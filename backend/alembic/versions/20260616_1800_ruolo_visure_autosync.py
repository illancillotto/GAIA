"""add ruolo visure autosync config and queue

Revision ID: 20260616_1800
Revises: 20260616_1400
Create Date: 2026-06-16
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20260616_1800"
down_revision: Union[str, None] = "20260616_1400"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "catasto_batches",
        sa.Column("batch_kind", sa.String(length=32), nullable=False, server_default="manual_batch"),
    )
    op.add_column("catasto_batches", sa.Column("credential_id", sa.Uuid(), nullable=True))
    op.create_index("ix_catasto_batches_batch_kind", "catasto_batches", ["batch_kind"], unique=False)
    op.create_index("ix_catasto_batches_credential_id", "catasto_batches", ["credential_id"], unique=False)
    op.create_foreign_key(
        "fk_catasto_batches_credential_id_catasto_credentials",
        "catasto_batches",
        "catasto_credentials",
        ["credential_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.alter_column("catasto_batches", "batch_kind", server_default=None)

    op.create_table(
        "catasto_ruolo_autosync_config",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("credential_id", sa.Uuid(), nullable=True),
        sa.Column("last_source_refresh_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_batch_started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("updated_by_user_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["credential_id"], ["catasto_credentials.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by_user_id"], ["application_users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_catasto_ruolo_autosync_config_user"),
    )
    op.create_index(
        "ix_catasto_ruolo_autosync_config_credential_id",
        "catasto_ruolo_autosync_config",
        ["credential_id"],
        unique=False,
    )
    op.create_index("ix_catasto_ruolo_autosync_config_user_id", "catasto_ruolo_autosync_config", ["user_id"], unique=False)

    op.create_table(
        "catasto_ruolo_autosync_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("ruolo_particella_id", sa.Uuid(), nullable=False),
        sa.Column("cat_particella_id", sa.Uuid(), nullable=True),
        sa.Column("comune", sa.String(length=255), nullable=True),
        sa.Column("comune_codice", sa.String(length=255), nullable=True),
        sa.Column("catasto", sa.String(length=64), nullable=False, server_default="Terreni"),
        sa.Column("foglio", sa.String(length=64), nullable=True),
        sa.Column("particella", sa.String(length=64), nullable=True),
        sa.Column("subalterno", sa.String(length=64), nullable=True),
        sa.Column("tipo_visura", sa.String(length=64), nullable=False, server_default="Sintetica"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("last_error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("linked_batch_id", sa.Uuid(), nullable=True),
        sa.Column("linked_request_id", sa.Uuid(), nullable=True),
        sa.Column("retry_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_enqueued_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["linked_batch_id"], ["catasto_batches.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["linked_request_id"], ["catasto_visure_requests.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["ruolo_particella_id"], ["ruolo_particelle.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "ruolo_particella_id", name="uq_catasto_ruolo_autosync_item_user_particella"),
    )
    for index_name, columns in (
        ("ix_catasto_ruolo_autosync_items_user_id", ["user_id"]),
        ("ix_catasto_ruolo_autosync_items_ruolo_particella_id", ["ruolo_particella_id"]),
        ("ix_catasto_ruolo_autosync_items_cat_particella_id", ["cat_particella_id"]),
        ("ix_catasto_ruolo_autosync_items_status", ["status"]),
        ("ix_catasto_ruolo_autosync_items_linked_batch_id", ["linked_batch_id"]),
        ("ix_catasto_ruolo_autosync_items_linked_request_id", ["linked_request_id"]),
        ("ix_catasto_ruolo_autosync_items_retry_after", ["retry_after"]),
    ):
        op.create_index(index_name, "catasto_ruolo_autosync_items", columns, unique=False)

    op.alter_column("catasto_ruolo_autosync_config", "enabled", server_default=None)
    op.alter_column("catasto_ruolo_autosync_items", "catasto", server_default=None)
    op.alter_column("catasto_ruolo_autosync_items", "tipo_visura", server_default=None)
    op.alter_column("catasto_ruolo_autosync_items", "status", server_default=None)
    op.alter_column("catasto_ruolo_autosync_items", "attempt_count", server_default=None)


def downgrade() -> None:
    for index_name in (
        "ix_catasto_ruolo_autosync_items_retry_after",
        "ix_catasto_ruolo_autosync_items_linked_request_id",
        "ix_catasto_ruolo_autosync_items_linked_batch_id",
        "ix_catasto_ruolo_autosync_items_status",
        "ix_catasto_ruolo_autosync_items_cat_particella_id",
        "ix_catasto_ruolo_autosync_items_ruolo_particella_id",
        "ix_catasto_ruolo_autosync_items_user_id",
    ):
        op.drop_index(index_name, table_name="catasto_ruolo_autosync_items")
    op.drop_table("catasto_ruolo_autosync_items")

    op.drop_index("ix_catasto_ruolo_autosync_config_user_id", table_name="catasto_ruolo_autosync_config")
    op.drop_index("ix_catasto_ruolo_autosync_config_credential_id", table_name="catasto_ruolo_autosync_config")
    op.drop_table("catasto_ruolo_autosync_config")

    op.drop_index("ix_catasto_batches_batch_kind", table_name="catasto_batches")
    op.drop_constraint("fk_catasto_batches_credential_id_catasto_credentials", "catasto_batches", type_="foreignkey")
    op.drop_index("ix_catasto_batches_credential_id", table_name="catasto_batches")
    op.drop_column("catasto_batches", "credential_id")
    op.drop_column("catasto_batches", "batch_kind")
