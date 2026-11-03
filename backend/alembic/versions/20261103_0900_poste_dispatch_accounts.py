"""Bind Poste lots to accounts and preserve the identity of upload operators."""

import sqlalchemy as sa

from alembic import op

revision = "20261103_0900"
down_revision = "20261028_1500"
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table("ruolo_poste_dispatch_lots") as batch:
        batch.add_column(sa.Column("credential_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("poste_username", sa.String(255), nullable=True))
        batch.add_column(sa.Column("credential_label", sa.String(120), nullable=True))
        batch.add_column(sa.Column("created_by_username", sa.String(255), nullable=True))
        batch.create_foreign_key(
            "fk_dispatch_lot_credential",
            "posta_online_credentials",
            ["credential_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("ix_ruolo_poste_dispatch_lots_credential_id", ["credential_id"])
    with op.batch_alter_table("ruolo_poste_dispatch_items") as batch:
        batch.add_column(sa.Column("upload_requested_by_user_id", sa.Integer(), nullable=True))
        batch.add_column(sa.Column("upload_requested_by_username", sa.String(255), nullable=True))
        batch.add_column(sa.Column("upload_job_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_dispatch_upload_actor",
            "application_users",
            ["upload_requested_by_user_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch.create_foreign_key(
            "fk_dispatch_upload_job",
            "posta_online_registered_mail_sync_jobs",
            ["upload_job_id"],
            ["id"],
            ondelete="SET NULL",
        )
    with op.batch_alter_table("ruolo_poste_dispatch_events") as batch:
        batch.add_column(sa.Column("actor_username", sa.String(255), nullable=True))
    # Existing explicit actor IDs are evidence; an account or uploader cannot be inferred.
    op.execute(
        sa.text(
            "UPDATE ruolo_poste_dispatch_lots SET created_by_username = "
            "(SELECT username FROM application_users WHERE id = created_by)"
        )
    )
    op.execute(
        sa.text(
            "UPDATE ruolo_poste_dispatch_events SET actor_username = "
            "(SELECT username FROM application_users WHERE id = actor_id)"
        )
    )


def downgrade():
    with op.batch_alter_table("ruolo_poste_dispatch_events") as batch:
        batch.drop_column("actor_username")
    with op.batch_alter_table("ruolo_poste_dispatch_items") as batch:
        batch.drop_constraint("fk_dispatch_upload_job", type_="foreignkey")
        batch.drop_constraint("fk_dispatch_upload_actor", type_="foreignkey")
        batch.drop_column("upload_job_id")
        batch.drop_column("upload_requested_by_username")
        batch.drop_column("upload_requested_by_user_id")
    with op.batch_alter_table("ruolo_poste_dispatch_lots") as batch:
        batch.drop_index("ix_ruolo_poste_dispatch_lots_credential_id")
        batch.drop_constraint("fk_dispatch_lot_credential", type_="foreignkey")
        batch.drop_column("credential_id")
        batch.drop_column("poste_username")
        batch.drop_column("credential_label")
        batch.drop_column("created_by_username")
