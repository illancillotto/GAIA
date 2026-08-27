"""Deduplicate and index the Ruolo autosync queue.

Revision ID: 20260827_0900
Revises: 20260826_1200
"""

from alembic import op

revision = "20260827_0900"
down_revision = "20260826_1200"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   row_number() OVER (
                       PARTITION BY user_id, cat_particella_id
                       ORDER BY
                           CASE status
                               WHEN 'completed' THEN 0
                               WHEN 'processing' THEN 1
                               WHEN 'queued' THEN 2
                               WHEN 'pending' THEN 3
                               WHEN 'blocked_runtime' THEN 4
                               WHEN 'blocked_source' THEN 5
                               ELSE 6
                           END,
                           updated_at DESC,
                           created_at DESC,
                           id
                   ) AS duplicate_rank
            FROM catasto_ruolo_autosync_items
            WHERE cat_particella_id IS NOT NULL
        )
        DELETE FROM catasto_ruolo_autosync_items AS item
        USING ranked
        WHERE item.id = ranked.id
          AND ranked.duplicate_rank > 1
        """
    )
    op.drop_constraint(
        "uq_catasto_ruolo_autosync_item_user_particella",
        "catasto_ruolo_autosync_items",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_catasto_ruolo_autosync_item_user_cat_particella",
        "catasto_ruolo_autosync_items",
        ["user_id", "cat_particella_id"],
    )
    op.create_index(
        "ix_catasto_ruolo_autosync_items_user_status",
        "catasto_ruolo_autosync_items",
        ["user_id", "status"],
    )
    op.create_index(
        "ix_catasto_ruolo_autosync_items_user_updated",
        "catasto_ruolo_autosync_items",
        ["user_id", "updated_at", "created_at"],
    )
    op.create_index(
        "ix_ruolo_particelle_created_at",
        "ruolo_particelle",
        ["created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_ruolo_particelle_created_at", table_name="ruolo_particelle")
    op.drop_index(
        "ix_catasto_ruolo_autosync_items_user_updated",
        table_name="catasto_ruolo_autosync_items",
    )
    op.drop_index(
        "ix_catasto_ruolo_autosync_items_user_status",
        table_name="catasto_ruolo_autosync_items",
    )
    op.drop_constraint(
        "uq_catasto_ruolo_autosync_item_user_cat_particella",
        "catasto_ruolo_autosync_items",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_catasto_ruolo_autosync_item_user_particella",
        "catasto_ruolo_autosync_items",
        ["user_id", "ruolo_particella_id"],
    )
