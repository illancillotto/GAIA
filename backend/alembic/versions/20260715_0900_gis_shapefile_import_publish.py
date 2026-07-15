"""add GIS shapefile import publish tracking

Revision ID: 20260715_0900
Revises: 20260714_1700
Create Date: 2026-07-15 09:00:00
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_0900"
down_revision: str | Sequence[str] | None = "20260714_1700"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("gis_shapefile_imports", sa.Column("published_layer_id", sa.Uuid(), nullable=True))
    op.add_column("gis_shapefile_imports", sa.Column("published_at", sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(
        "fk_gis_shapefile_imports_published_layer_id",
        "gis_shapefile_imports",
        "gis_layers",
        ["published_layer_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index(
        op.f("ix_gis_shapefile_imports_published_layer_id"),
        "gis_shapefile_imports",
        ["published_layer_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_gis_shapefile_imports_published_layer_id"), table_name="gis_shapefile_imports")
    op.drop_constraint("fk_gis_shapefile_imports_published_layer_id", "gis_shapefile_imports", type_="foreignkey")
    op.drop_column("gis_shapefile_imports", "published_at")
    op.drop_column("gis_shapefile_imports", "published_layer_id")
