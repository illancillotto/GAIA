"""Posta Online outbox for drafts that an operator sends manually on Poste."""

import sqlalchemy as sa

from alembic import op

revision = "20261028_1500"
down_revision = "20261028_0900"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ruolo_poste_dispatch_lots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("postal_options", sa.JSON(), nullable=False),
        sa.Column("portal_snapshot", sa.JSON(), nullable=True),
        sa.Column(
            "created_by",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_ruolo_poste_dispatch_lots_status", "ruolo_poste_dispatch_lots", ["status"])
    op.create_table(
        "ruolo_poste_dispatch_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "lot_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_poste_dispatch_lots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "batch_item_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_tributi_reminder_batch_items.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("notice_number", sa.String(40), nullable=False),
        sa.Column("shipment_name", sa.String(40), nullable=False),
        sa.Column("active_key", sa.String(40), nullable=True),
        sa.Column("active_source_key", sa.String(40), nullable=True),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("recipient", sa.JSON(), nullable=False),
        sa.Column("poste_address", sa.JSON(), nullable=True),
        sa.Column("address_review", sa.JSON(), nullable=True),
        sa.Column("artifact", sa.LargeBinary(), nullable=True),
        sa.Column("artifact_sha256", sa.String(64), nullable=False),
        sa.Column("artifact_size", sa.Integer(), nullable=False),
        sa.Column("poste_draft_id", sa.String(32), nullable=True),
        sa.Column("poste_status", sa.String(80), nullable=True),
        sa.Column("price_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("draft_created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("tracking_number", sa.String(40), nullable=True),
        sa.Column(
            "registered_mail_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_tributi_registered_mails.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("error_detail", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("active_key", name="uq_poste_dispatch_item_active_key"),
        sa.UniqueConstraint("active_source_key", name="uq_poste_dispatch_item_active_source"),
    )
    for column in ("lot_id", "batch_item_id", "shipment_name", "status"):
        op.create_index(
            f"ix_ruolo_poste_dispatch_items_{column}", "ruolo_poste_dispatch_items", [column]
        )
    op.create_table(
        "ruolo_poste_dispatch_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "lot_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_poste_dispatch_lots.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "item_id",
            sa.Uuid(),
            sa.ForeignKey("ruolo_poste_dispatch_items.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("kind", sa.String(40), nullable=False),
        sa.Column("from_status", sa.String(24), nullable=True),
        sa.Column("to_status", sa.String(24), nullable=True),
        sa.Column(
            "actor_id",
            sa.Integer(),
            sa.ForeignKey("application_users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("job_id", sa.Integer(), nullable=True),
        sa.Column("detail", sa.JSON(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index(
        "ix_ruolo_poste_dispatch_events_lot_id", "ruolo_poste_dispatch_events", ["lot_id"]
    )
    op.create_index(
        "ix_ruolo_poste_dispatch_events_item_id", "ruolo_poste_dispatch_events", ["item_id"]
    )


def downgrade():
    op.drop_table("ruolo_poste_dispatch_events")
    op.drop_table("ruolo_poste_dispatch_items")
    op.drop_table("ruolo_poste_dispatch_lots")
