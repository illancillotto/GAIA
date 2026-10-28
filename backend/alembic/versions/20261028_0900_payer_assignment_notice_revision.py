"""Invalidate prepared notices when their payer assignment changes."""

from alembic import op

revision = "20261028_0900"
down_revision = "20261027_1300"
branch_labels = None
depends_on = None
TABLE = "ruolo_tributi_payer_assignments"


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return
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
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute(f"DROP TRIGGER gaia_notice_revision_truncate ON {TABLE}")
    op.execute(f"DROP TRIGGER gaia_notice_revision_row ON {TABLE}")
