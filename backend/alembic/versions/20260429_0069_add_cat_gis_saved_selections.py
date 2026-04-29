"""add catasto gis saved selections

Revision ID: 20260429_0069
Revises: 20260429_0068
Create Date: 2026-04-29 09:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260429_0069"
down_revision: str | None = "20260429_0068"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "cat_gis_saved_selections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("color", sa.String(length=16), nullable=False, server_default="#10B981"),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("n_particelle", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("n_with_geometry", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("import_summary", sa.JSON(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["application_users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_cat_gis_saved_selections_created_by"), "cat_gis_saved_selections", ["created_by"])

    op.create_table(
        "cat_gis_saved_selection_items",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("selection_id", sa.Uuid(), nullable=False),
        sa.Column("particella_id", sa.Uuid(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_row_index", sa.Integer(), nullable=True),
        sa.Column("source_ref", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["particella_id"], ["cat_particelle.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["selection_id"], ["cat_gis_saved_selections.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("selection_id", "particella_id", name="uq_cat_gis_saved_selection_particella"),
    )
    op.create_index(
        op.f("ix_cat_gis_saved_selection_items_particella_id"),
        "cat_gis_saved_selection_items",
        ["particella_id"],
    )
    op.create_index(
        op.f("ix_cat_gis_saved_selection_items_selection_id"),
        "cat_gis_saved_selection_items",
        ["selection_id"],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_cat_gis_saved_selection_items_selection_id"), table_name="cat_gis_saved_selection_items")
    op.drop_index(op.f("ix_cat_gis_saved_selection_items_particella_id"), table_name="cat_gis_saved_selection_items")
    op.drop_table("cat_gis_saved_selection_items")
    op.drop_index(op.f("ix_cat_gis_saved_selections_created_by"), table_name="cat_gis_saved_selections")
    op.drop_table("cat_gis_saved_selections")
