"""catasto: add distretti geometry history table

Revision ID: 20260429_0070
Revises: 20260429_0069
Create Date: 2026-04-29
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geometry


# revision identifiers, used by Alembic.
revision = "20260429_0070"
down_revision = "20260429_0069"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "cat_distretti_geometry_versions",
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        sa.Column(
            "distretto_id",
            sa.Uuid(),
            sa.ForeignKey("cat_distretti.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "source_batch_id",
            sa.Uuid(),
            sa.ForeignKey("cat_import_batches.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("num_distretto", sa.String(length=10), nullable=False),
        sa.Column("nome_distretto", sa.String(length=200), nullable=True),
        sa.Column("geometry", Geometry("MULTIPOLYGON", srid=4326), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date(), nullable=True),
        sa.Column("is_current", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index(
        "ix_cat_distretti_geometry_versions_distretto_id",
        "cat_distretti_geometry_versions",
        ["distretto_id"],
    )
    op.create_index(
        "ix_cat_distretti_geometry_versions_source_batch_id",
        "cat_distretti_geometry_versions",
        ["source_batch_id"],
    )
    op.create_index(
        "ix_cat_distretti_geometry_versions_num_distretto",
        "cat_distretti_geometry_versions",
        ["num_distretto"],
    )
    op.create_index(
        "ix_cat_distretti_geometry_versions_is_current",
        "cat_distretti_geometry_versions",
        ["is_current"],
    )
    op.create_index(
        "idx_cat_distretti_geometry_versions_geom",
        "cat_distretti_geometry_versions",
        ["geometry"],
        unique=False,
        postgresql_using="gist",
    )
    op.execute(
        """
        CREATE UNIQUE INDEX uq_cat_distretti_geometry_versions_current
        ON cat_distretti_geometry_versions (distretto_id)
        WHERE is_current = true
        """
    )
    op.execute(
        """
        INSERT INTO cat_distretti_geometry_versions (
            id,
            distretto_id,
            source_batch_id,
            source_filename,
            num_distretto,
            nome_distretto,
            geometry,
            valid_from,
            valid_to,
            is_current,
            created_at
        )
        SELECT
            gen_random_uuid(),
            d.id,
            NULL,
            'legacy_bootstrap',
            d.num_distretto,
            d.nome_distretto,
            d.geometry,
            COALESCE(d.created_at::date, CURRENT_DATE),
            NULL,
            true,
            COALESCE(d.updated_at, d.created_at, now())
        FROM cat_distretti d
        WHERE d.geometry IS NOT NULL
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_cat_distretti_geometry_versions_current")
    op.drop_index("idx_cat_distretti_geometry_versions_geom", table_name="cat_distretti_geometry_versions")
    op.drop_index("ix_cat_distretti_geometry_versions_is_current", table_name="cat_distretti_geometry_versions")
    op.drop_index("ix_cat_distretti_geometry_versions_num_distretto", table_name="cat_distretti_geometry_versions")
    op.drop_index("ix_cat_distretti_geometry_versions_source_batch_id", table_name="cat_distretti_geometry_versions")
    op.drop_index("ix_cat_distretti_geometry_versions_distretto_id", table_name="cat_distretti_geometry_versions")
    op.drop_table("cat_distretti_geometry_versions")
