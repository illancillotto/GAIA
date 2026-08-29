"""Create GIS territory sheet persistence.

Revision ID: 20260901_0900
Revises: 20260827_1100
"""

from alembic import op

revision = "20260901_0900"
down_revision = "20260827_1100"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE gis_schede_territoriali (
            id UUID PRIMARY KEY,
            particella_id UUID NOT NULL REFERENCES cat_particelle(id) ON DELETE RESTRICT,
            requested_by_user_id INTEGER REFERENCES application_users(id) ON DELETE SET NULL,
            status VARCHAR(32) NOT NULL,
            artifact_path TEXT,
            checksum_sha256 VARCHAR(64),
            source_snapshot_json JSON NOT NULL,
            error_message TEXT,
            requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            completed_at TIMESTAMPTZ,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_gis_schede_territoriali_particella "
        "ON gis_schede_territoriali (particella_id)"
    )
    op.execute(
        "CREATE INDEX ix_gis_schede_territoriali_requested_by "
        "ON gis_schede_territoriali (requested_by_user_id)"
    )
    op.execute(
        "CREATE INDEX ix_gis_schede_territoriali_status "
        "ON gis_schede_territoriali (status)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS gis_schede_territoriali")
