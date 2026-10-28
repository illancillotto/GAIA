"""Store personalized portal access with encrypted PIN and revision invalidation."""

import sqlalchemy as sa
from alembic import op

revision = "20261027_1100"
down_revision = "20261027_0900"
branch_labels = None
depends_on = None
TABLE = "ruolo_taxpayer_portal_access"


def upgrade():
    op.create_table(
        TABLE,
        sa.Column("account_code", sa.String(32), primary_key=True),
        sa.Column("tax_code", sa.String(32), nullable=False),
        sa.Column("pin_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("source_sha256", sa.String(64), nullable=False),
        sa.Column("imported_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_ruolo_taxpayer_portal_access_tax_code", TABLE, ["tax_code"])
    if op.get_bind().dialect.name == "postgresql":
        op.execute(f"""
            CREATE CONSTRAINT TRIGGER gaia_notice_revision_row
            AFTER INSERT OR UPDATE OR DELETE ON {TABLE}
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
            EXECUTE FUNCTION gaia_notice_revision_bump()
        """)
        op.execute(f"""
            CREATE TRIGGER gaia_notice_revision_truncate
            AFTER TRUNCATE ON {TABLE} FOR EACH STATEMENT
            EXECUTE FUNCTION gaia_notice_revision_bump()
        """)
        op.execute(f"ALTER TABLE {TABLE} ENABLE ALWAYS TRIGGER gaia_notice_revision_row")
        op.execute(f"ALTER TABLE {TABLE} ENABLE ALWAYS TRIGGER gaia_notice_revision_truncate")


def downgrade():
    op.drop_table(TABLE)
