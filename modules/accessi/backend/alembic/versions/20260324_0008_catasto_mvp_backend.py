"""catasto mvp backend

Revision ID: 20260324_0008
Revises: 20260323_0007
Create Date: 2026-03-24 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "20260324_0008"
down_revision = "20260323_0007"
branch_labels = None
depends_on = None


CATASO_COMUNI_SEED = [
    {"nome": "Terralba", "codice_sister": "L122#TERRALBA#2#2", "ufficio": "ORISTANO Territorio"},
    {"nome": "Uras", "codice_sister": "L496#URAS#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Marrubiu", "codice_sister": "E972#MARRUBIU#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Narbolia", "codice_sister": "F840#NARBOLIA#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Santa Giusta", "codice_sister": "I205#SANTA GIUSTA#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Palmas Arborea", "codice_sister": "G286#PALMAS ARBOREA#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Mogoro", "codice_sister": "F272#MOGORO#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Zerfaliu", "codice_sister": "M168#ZERFALIU#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Bauladu", "codice_sister": "A721#BAULADU#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "San Vero Milis", "codice_sister": "I384#SAN VERO MILIS#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Tramatza", "codice_sister": "L321#TRAMATZA#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Riola Sardo", "codice_sister": "H301#RIOLA SARDO#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Nurachi", "codice_sister": "F980#NURACHI#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Siamaggiore", "codice_sister": "I717#SIAMAGGIORE#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Baratili San Pietro", "codice_sister": "A621#BARATILI SAN PIETRO#2#2", "ufficio": "ORISTANO Territorio"},
    {"nome": "Ollastra", "codice_sister": "G043#OLLASTRA#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Solarussa", "codice_sister": "I791#SOLARUSSA#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Cabras", "codice_sister": "B314#CABRAS#2#2", "ufficio": "ORISTANO Territorio"},
    {"nome": "Arborea", "codice_sister": "A357#ARBOREA#3#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Simaxis", "codice_sister": "I743#SIMAXIS#2#2", "ufficio": "ORISTANO Territorio"},
    {"nome": "Oristano", "codice_sister": "G113#ORISTANO#5#5", "ufficio": "ORISTANO Territorio"},
    {"nome": "Zeddiani", "codice_sister": "M153#ZEDDIANI#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Milis", "codice_sister": "F208#MILIS#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "San Nicolo d'Arcidano", "codice_sister": "A368#SAN NICOLO' D'ARCIDANO#0#0", "ufficio": "ORISTANO Territorio"},
    {"nome": "Sili", "codice_sister": "G113#ORISTANO#5#5", "ufficio": "ORISTANO Territorio"},
    {"nome": "Nuraxinieddu", "codice_sister": "G113#ORISTANO#5#5", "ufficio": "ORISTANO Territorio"},
    {"nome": "Massama", "codice_sister": "G113#ORISTANO#5#5", "ufficio": "ORISTANO Territorio"},
    {"nome": "Donigala", "codice_sister": "G113#ORISTANO#5#5", "ufficio": "ORISTANO Territorio"},
]


def upgrade() -> None:
    op.create_table(
        "catasto_credentials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sister_username", sa.String(length=128), nullable=False),
        sa.Column("sister_password_encrypted", sa.LargeBinary(), nullable=False),
        sa.Column("convenzione", sa.Text(), nullable=True),
        sa.Column("codice_richiesta", sa.String(length=128), nullable=True),
        sa.Column("ufficio_provinciale", sa.String(length=255), nullable=False, server_default="ORISTANO Territorio"),
        sa.Column("verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", name="uq_catasto_credentials_user_id"),
    )
    op.create_index("ix_catasto_credentials_user_id", "catasto_credentials", ["user_id"], unique=False)

    op.create_table(
        "catasto_batches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("total_items", sa.Integer(), nullable=False),
        sa.Column("completed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("failed_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("skipped_items", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("source_filename", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catasto_batches_user_id", "catasto_batches", ["user_id"], unique=False)
    op.create_index("ix_catasto_batches_status", "catasto_batches", ["status"], unique=False)

    op.create_table(
        "catasto_comuni",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("nome", sa.String(length=255), nullable=False),
        sa.Column("codice_sister", sa.String(length=255), nullable=False),
        sa.Column("ufficio", sa.String(length=255), nullable=False, server_default="ORISTANO Territorio"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("nome", "ufficio", name="uq_catasto_comuni_nome_ufficio"),
    )
    op.create_index("ix_catasto_comuni_nome", "catasto_comuni", ["nome"], unique=False)

    op.create_table(
        "catasto_documents",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=True),
        sa.Column("comune", sa.String(length=255), nullable=False),
        sa.Column("foglio", sa.String(length=64), nullable=False),
        sa.Column("particella", sa.String(length=64), nullable=False),
        sa.Column("subalterno", sa.String(length=64), nullable=True),
        sa.Column("catasto", sa.String(length=64), nullable=False),
        sa.Column("tipo_visura", sa.String(length=64), nullable=False),
        sa.Column("filename", sa.String(length=255), nullable=False),
        sa.Column("filepath", sa.String(length=1024), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=True),
        sa.Column("codice_fiscale", sa.String(length=64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_catasto_documents_request_id"),
    )
    op.create_index("ix_catasto_documents_user_id", "catasto_documents", ["user_id"], unique=False)
    op.create_index("ix_catasto_documents_comune", "catasto_documents", ["comune"], unique=False)

    op.create_table(
        "catasto_visure_requests",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("batch_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False),
        sa.Column("comune", sa.String(length=255), nullable=False),
        sa.Column("comune_codice", sa.String(length=255), nullable=True),
        sa.Column("catasto", sa.String(length=64), nullable=False),
        sa.Column("sezione", sa.String(length=64), nullable=True),
        sa.Column("foglio", sa.String(length=64), nullable=False),
        sa.Column("particella", sa.String(length=64), nullable=False),
        sa.Column("subalterno", sa.String(length=64), nullable=True),
        sa.Column("tipo_visura", sa.String(length=64), nullable=False, server_default="Sintetica"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="pending"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("document_id", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["batch_id"], ["catasto_batches.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["document_id"], ["catasto_documents.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["application_users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("batch_id", "row_index", name="uq_catasto_visure_requests_batch_row"),
    )
    op.create_index("ix_catasto_visure_requests_batch_id", "catasto_visure_requests", ["batch_id"], unique=False)
    op.create_index("ix_catasto_visure_requests_user_id", "catasto_visure_requests", ["user_id"], unique=False)
    op.create_index("ix_catasto_visure_requests_status", "catasto_visure_requests", ["status"], unique=False)

    op.create_foreign_key(
        "fk_catasto_documents_request_id",
        "catasto_documents",
        "catasto_visure_requests",
        ["request_id"],
        ["id"],
        ondelete="SET NULL",
    )

    op.create_table(
        "catasto_captcha_log",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("image_path", sa.String(length=1024), nullable=False),
        sa.Column("ocr_text", sa.String(length=64), nullable=True),
        sa.Column("manual_text", sa.String(length=64), nullable=True),
        sa.Column("is_correct", sa.Boolean(), nullable=True),
        sa.Column("method", sa.String(length=32), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["request_id"], ["catasto_visure_requests.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_catasto_captcha_log_request_id", "catasto_captcha_log", ["request_id"], unique=False)

    comuni_table = sa.table(
        "catasto_comuni",
        sa.column("nome", sa.String()),
        sa.column("codice_sister", sa.String()),
        sa.column("ufficio", sa.String()),
    )
    op.bulk_insert(comuni_table, CATASO_COMUNI_SEED)


def downgrade() -> None:
    op.drop_table("catasto_captcha_log")
    op.drop_constraint("fk_catasto_documents_request_id", "catasto_documents", type_="foreignkey")
    op.drop_table("catasto_visure_requests")
    op.drop_table("catasto_documents")
    op.drop_table("catasto_comuni")
    op.drop_table("catasto_batches")
    op.drop_table("catasto_credentials")
