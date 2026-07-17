"""riordino blocks

Revision ID: 20260717_0900
Revises: 20260716_1300
Create Date: 2026-07-17
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "20260717_0900"
down_revision = "20260716_1300"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "riordino_blocks",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("code", sa.String(length=24), nullable=False, unique=True),
        sa.Column("title", sa.String(length=300), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("municipality", sa.String(length=100), nullable=True),
        sa.Column("selection_type", sa.String(length=32), nullable=False),
        sa.Column("selection_json", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False, server_default="draft"),
        sa.Column("coordinator_user_id", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("parcel_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("mismatch_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_riordino_blocks_status", "riordino_blocks", ["status"])
    op.create_index("ix_riordino_blocks_municipality", "riordino_blocks", ["municipality"])
    op.create_index("ix_riordino_blocks_coordinator_user_id", "riordino_blocks", ["coordinator_user_id"])
    op.create_index("ix_riordino_blocks_created_at", "riordino_blocks", ["created_at"])
    op.create_index("ix_riordino_blocks_deleted_at", "riordino_blocks", ["deleted_at"])
    op.alter_column("riordino_blocks", "status", server_default=None)
    op.alter_column("riordino_blocks", "parcel_count", server_default=None)
    op.alter_column("riordino_blocks", "mismatch_count", server_default=None)

    op.create_table(
        "riordino_block_assignments",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("block_id", sa.Uuid(), sa.ForeignKey("riordino_blocks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("assignment_role", sa.String(length=24), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=False),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("block_id", "user_id", "assignment_role", name="uq_riordino_block_assignments_user_role"),
    )
    op.create_index("ix_riordino_block_assignments_block_id", "riordino_block_assignments", ["block_id"])
    op.create_index("ix_riordino_block_assignments_user_id", "riordino_block_assignments", ["user_id"])
    op.create_index("ix_riordino_block_assignments_role", "riordino_block_assignments", ["assignment_role"])
    op.alter_column("riordino_block_assignments", "is_active", server_default=None)

    op.create_table(
        "riordino_block_parcel_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column("block_id", sa.Uuid(), sa.ForeignKey("riordino_blocks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("ade_particella_id", sa.Uuid(), sa.ForeignKey("cat_ade_particelle.id", ondelete="SET NULL"), nullable=True),
        sa.Column("national_cadastral_reference", sa.String(length=80), nullable=False),
        sa.Column("administrative_unit", sa.String(length=4), nullable=True),
        sa.Column("codice_catastale", sa.String(length=4), nullable=True),
        sa.Column("sezione_catastale", sa.String(length=10), nullable=True),
        sa.Column("foglio", sa.String(length=10), nullable=True),
        sa.Column("particella", sa.String(length=20), nullable=True),
        sa.Column("label", sa.String(length=80), nullable=True),
        sa.Column("ade_payload_json", sa.JSON(), nullable=True),
        sa.Column("cat_particella_id", sa.Uuid(), sa.ForeignKey("cat_particelle.id", ondelete="SET NULL"), nullable=True),
        sa.Column("cat_particella_match_status", sa.String(length=24), nullable=False),
        sa.Column("cat_particella_match_reason", sa.Text(), nullable=True),
        sa.Column("capacitas_payload_json", sa.JSON(), nullable=True),
        sa.Column("operator_review_status", sa.String(length=24), nullable=False, server_default="pending"),
        sa.Column("operator_review_notes", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sister_visura_status", sa.String(length=24), nullable=False, server_default="not_requested"),
        sa.Column("sister_visura_request_id", sa.String(length=80), nullable=True),
        sa.Column("sister_visura_document_ref", sa.String(length=255), nullable=True),
        sa.Column("sister_visura_error", sa.Text(), nullable=True),
        sa.Column("sister_visura_requested_by", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("sister_visura_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sister_visura_completed_by", sa.Integer(), sa.ForeignKey("application_users.id"), nullable=True),
        sa.Column("sister_visura_completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("block_id", "national_cadastral_reference", name="uq_riordino_block_snapshot_ref"),
    )
    op.create_index("ix_riordino_block_parcel_snapshots_block_id", "riordino_block_parcel_snapshots", ["block_id"])
    op.create_index("ix_riordino_block_parcel_snapshots_ade_id", "riordino_block_parcel_snapshots", ["ade_particella_id"])
    op.create_index(
        "ix_riordino_block_parcel_snapshots_match_status",
        "riordino_block_parcel_snapshots",
        ["cat_particella_match_status"],
    )
    op.create_index(
        "ix_riordino_block_parcel_snapshots_foglio_particella",
        "riordino_block_parcel_snapshots",
        ["foglio", "particella"],
    )
    op.alter_column("riordino_block_parcel_snapshots", "operator_review_status", server_default=None)
    op.alter_column("riordino_block_parcel_snapshots", "sister_visura_status", server_default=None)

    op.add_column("riordino_practices", sa.Column("block_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_riordino_practices_block_id",
        "riordino_practices",
        "riordino_blocks",
        ["block_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_riordino_practices_block_id", "riordino_practices", ["block_id"])

    op.add_column("riordino_events", sa.Column("block_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_riordino_events_block_id",
        "riordino_events",
        "riordino_blocks",
        ["block_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.alter_column("riordino_events", "practice_id", nullable=True)
    op.create_index("ix_riordino_events_block_created", "riordino_events", ["block_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_riordino_events_block_created", table_name="riordino_events")
    op.alter_column("riordino_events", "practice_id", nullable=False)
    op.drop_constraint("fk_riordino_events_block_id", "riordino_events", type_="foreignkey")
    op.drop_column("riordino_events", "block_id")

    op.drop_index("ix_riordino_practices_block_id", table_name="riordino_practices")
    op.drop_constraint("fk_riordino_practices_block_id", "riordino_practices", type_="foreignkey")
    op.drop_column("riordino_practices", "block_id")

    op.drop_index("ix_riordino_block_parcel_snapshots_foglio_particella", table_name="riordino_block_parcel_snapshots")
    op.drop_index("ix_riordino_block_parcel_snapshots_match_status", table_name="riordino_block_parcel_snapshots")
    op.drop_index("ix_riordino_block_parcel_snapshots_ade_id", table_name="riordino_block_parcel_snapshots")
    op.drop_index("ix_riordino_block_parcel_snapshots_block_id", table_name="riordino_block_parcel_snapshots")
    op.drop_table("riordino_block_parcel_snapshots")

    op.drop_index("ix_riordino_block_assignments_role", table_name="riordino_block_assignments")
    op.drop_index("ix_riordino_block_assignments_user_id", table_name="riordino_block_assignments")
    op.drop_index("ix_riordino_block_assignments_block_id", table_name="riordino_block_assignments")
    op.drop_table("riordino_block_assignments")

    op.drop_index("ix_riordino_blocks_deleted_at", table_name="riordino_blocks")
    op.drop_index("ix_riordino_blocks_created_at", table_name="riordino_blocks")
    op.drop_index("ix_riordino_blocks_coordinator_user_id", table_name="riordino_blocks")
    op.drop_index("ix_riordino_blocks_municipality", table_name="riordino_blocks")
    op.drop_index("ix_riordino_blocks_status", table_name="riordino_blocks")
    op.drop_table("riordino_blocks")
