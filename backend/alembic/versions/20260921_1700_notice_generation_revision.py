"""Commit revision for future notice confirmation; does not enable confirmation.

Revision ID: 20260921_1700
Revises: 20260921_1500
"""

from uuid import uuid4

from alembic import op
import sqlalchemy as sa

revision = "20260921_1700"
down_revision = "20260921_1500"
branch_labels = None
depends_on = None

# Frozen migration contract; runtime/tests verify parity, never import app code.
DEPENDENCY_TABLES = (
    "ana_subjects", "ana_persons", "ana_companies", "ana_payment_notices",
    "ruolo_avvisi", "ruolo_partite", "ruolo_particelle",
    "ruolo_tributi_payments", "ruolo_tributi_avviso_status",
    "ruolo_tributi_special_notices", "ruolo_tributi_special_allocations",
    "ruolo_tributi_year_managers", "ruolo_tributi_calculation_policies",
    "ruolo_tributi_templates", "ruolo_tributi_registered_mails",
    "ruolo_notice_documents", "ruolo_notice_positions", "ruolo_notice_attempts",
    "ruolo_notice_evidence", "ruolo_notice_notifications", "ruolo_notice_recoveries",
    "ruolo_notice_import_batches", "ruolo_notice_import_rows",
)


def upgrade():
    op.create_table(
        "ruolo_notice_generation_revision",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=False),
        sa.Column("epoch", sa.Uuid(), nullable=False),
        sa.Column("revision", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("last_transaction_id", sa.BigInteger(), nullable=False, server_default=sa.text("0")),
        sa.CheckConstraint("id = 1", name="ck_notice_generation_revision_singleton"),
        sa.CheckConstraint("revision >= 0", name="ck_notice_generation_revision_positive"),
    )
    if op.get_bind().dialect.name != "postgresql":
        return  # SQLite metadata tests only; runtime refuses this dialect.
    table = sa.table("ruolo_notice_generation_revision", sa.column("id", sa.Integer()), sa.column("epoch", sa.Uuid()))
    op.bulk_insert(table, [{"id": 1, "epoch": uuid4()}])
    op.execute("""
        CREATE FUNCTION gaia_notice_revision_bump() RETURNS trigger
        LANGUAGE plpgsql AS $$
        DECLARE revision_exists boolean;
        BEGIN
            EXECUTE format(
                'UPDATE %I.ruolo_notice_generation_revision '
                'SET revision = revision + 1, last_transaction_id = txid_current() '
                'WHERE id = 1 AND last_transaction_id <> txid_current()', TG_TABLE_SCHEMA);
            EXECUTE format(
                'SELECT EXISTS (SELECT 1 FROM %I.ruolo_notice_generation_revision WHERE id = 1)',
                TG_TABLE_SCHEMA) INTO revision_exists;
            IF NOT revision_exists THEN
                RAISE EXCEPTION 'Notice generation revision is missing';
            END IF;
            RETURN NULL;
        END;
        $$
    """)
    for table_name in DEPENDENCY_TABLES:
        op.execute(f"""
            CREATE CONSTRAINT TRIGGER gaia_notice_revision_row
            AFTER INSERT OR UPDATE OR DELETE ON {table_name}
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
            EXECUTE FUNCTION gaia_notice_revision_bump()
        """)
        op.execute(f"""
            CREATE TRIGGER gaia_notice_revision_truncate
            AFTER TRUNCATE ON {table_name} FOR EACH STATEMENT
            EXECUTE FUNCTION gaia_notice_revision_bump()
        """)
        op.execute(f"ALTER TABLE {table_name} ENABLE ALWAYS TRIGGER gaia_notice_revision_row")
        op.execute(f"ALTER TABLE {table_name} ENABLE ALWAYS TRIGGER gaia_notice_revision_truncate")


def downgrade():
    if op.get_bind().dialect.name == "postgresql":
        for table_name in reversed(DEPENDENCY_TABLES):
            op.execute(f"DROP TRIGGER gaia_notice_revision_truncate ON {table_name}")
            op.execute(f"DROP TRIGGER gaia_notice_revision_row ON {table_name}")
        op.execute("DROP FUNCTION gaia_notice_revision_bump()")
    op.drop_table("ruolo_notice_generation_revision")
