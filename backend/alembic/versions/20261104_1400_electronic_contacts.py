"""Typed anagrafica contacts for both individuals and companies; no data inference."""

import sqlalchemy as sa

from alembic import op

revision = "20261104_1400"
down_revision = "20261103_1200"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "ana_electronic_contacts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "subject_id",
            sa.Uuid(),
            sa.ForeignKey("ana_subjects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("address", sa.String(254), nullable=False),
        sa.Column("channel", sa.String(16), nullable=False),
        sa.Column("state", sa.String(12), nullable=False),
        sa.Column("source", sa.String(80), nullable=False),
        sa.Column("evidence_reference", sa.String(500), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("updated_by", sa.Integer(), sa.ForeignKey("application_users.id")),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("subject_id", "address", name="uq_ana_econtact_address"),
        sa.CheckConstraint(
            "channel IN ('pec','email','unclassified')", name="ck_ana_econtact_channel"
        ),
        sa.CheckConstraint("state IN ('active','review','revoked')", name="ck_ana_econtact_state"),
        sa.CheckConstraint(
            "channel <> 'unclassified' OR state <> 'active'", name="ck_ana_econtact_classified"
        ),
        sa.CheckConstraint("version > 0", name="ck_ana_econtact_version"),
    )
    op.create_index(
        "ix_ana_electronic_contacts_subject_id", "ana_electronic_contacts", ["subject_id"]
    )
    if op.get_bind().dialect.name == "postgresql":
        op.execute("""
            CREATE CONSTRAINT TRIGGER gaia_notice_revision_row
            AFTER INSERT OR UPDATE OR DELETE ON ana_electronic_contacts
            DEFERRABLE INITIALLY DEFERRED FOR EACH ROW
            EXECUTE FUNCTION gaia_notice_revision_bump()
        """)
        op.execute("""
            CREATE TRIGGER gaia_notice_revision_truncate
            AFTER TRUNCATE ON ana_electronic_contacts FOR EACH STATEMENT
            EXECUTE FUNCTION gaia_notice_revision_bump()
        """)
        op.execute(
            "ALTER TABLE ana_electronic_contacts ENABLE ALWAYS TRIGGER gaia_notice_revision_row"
        )
        op.execute(
            "ALTER TABLE ana_electronic_contacts ENABLE ALWAYS TRIGGER gaia_notice_revision_truncate"
        )


def downgrade():
    op.drop_table("ana_electronic_contacts")
