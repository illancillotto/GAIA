"""add cat comuni reference and cod_comune_capacitas fields

Revision ID: 20260421_0053
Revises: 20260420_0051
Create Date: 2026-04-21
"""

from alembic import op
import sqlalchemy as sa


revision = "20260421_0053"
down_revision = "20260420_0051"
branch_labels = None
depends_on = None


COMUNI_ROWS = [
    (50, "Mogoro", "F272", 115035, 95029, "Mogoro", 95, "OR", "Sardegna"),
    (59, "Masullas", "F050", 115031, 95026, "Masullas", 95, "OR", "Sardegna"),
    (165, "Arborea", "A357", 115006, 95006, "Arborea", 95, "OR", "Sardegna"),
    (170, "Milis", "F208", 115032, 95027, "Milis", 95, "OR", "Sardegna"),
    (173, "Bauladu", "A721", 115013, 95013, "Bauladu", 95, "OR", "Sardegna"),
    (176, "Narbolia", "F840", 115038, 95031, "Narbolia", 95, "OR", "Sardegna"),
    (179, "San Vero Milis", "I384", 115055, 95050, "San Vero Milis", 95, "OR", "Sardegna"),
    (186, "Tramatza", "L321", 115077, 95066, "Tramatza", 95, "OR", "Sardegna"),
    (189, "Zeddiani", "M153", 115086, 95074, "Zeddiani", 95, "OR", "Sardegna"),
    (200, "Oristano", "G113", 115045, 95038, "Oristano*Oristano", 95, "OR", "Sardegna"),
    (206, "Baratili San Pietro", "A621", 115011, 95011, "Baratili San Pietro", 95, "OR", "Sardegna"),
    (212, "Cabras", "B314", 115019, 95018, "Cabras", 95, "OR", "Sardegna"),
    (222, "Nurachi", "F980", 115042, 95035, "Nurachi", 95, "OR", "Sardegna"),
    (226, "Ollastra", "G043", 115044, 95037, "Ollastra Simaxis", 95, "OR", "Sardegna"),
    (229, "Palmas Arborea", "G286", 115046, 95039, "Palmas Arborea", 95, "OR", "Sardegna"),
    (232, "Riola Sardo", "H301", 115050, 95043, "Riola Sardo", 95, "OR", "Sardegna"),
    (239, "Santa Giusta", "I205", 115056, 95047, "Santa Giusta", 95, "OR", "Sardegna"),
    (242, "Siamaggiore", "I717", 115063, 95056, "Siamaggiore", 95, "OR", "Sardegna"),
    (249, "Simaxis", "I743", 115067, 95059, "Simaxis*Simaxis", 95, "OR", "Sardegna"),
    (252, "Solarussa", "I791", 115071, 95062, "Solarussa", 95, "OR", "Sardegna"),
    (266, "Zerfaliu", "M168", 115087, 95075, "Zerfaliu", 95, "OR", "Sardegna"),
    (280, "Terralba", "L122", 115075, 95065, "Terralba", 95, "OR", "Sardegna"),
    (283, "Marrubiu", "E972", 115030, 95025, "Marrubiu", 95, "OR", "Sardegna"),
    (286, "San Nicolo d'Arcidano", "A368", 115054, 95046, "San Nicolo Arcidano", 95, "OR", "Sardegna"),
    (289, "Uras", "L496", 115080, 95069, "Uras", 95, "OR", "Sardegna"),
    (743, "Pabillonis", "G207", 117011, 111052, "Pabillonis", 111, "SU", "Sardegna"),
]


def upgrade() -> None:
    op.create_table(
        "cat_comuni",
        sa.Column("id", sa.Uuid(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("nome_comune", sa.String(length=100), nullable=False),
        sa.Column("codice_catastale", sa.String(length=4), nullable=False),
        sa.Column("cod_comune_capacitas", sa.Integer(), nullable=False),
        sa.Column("codice_comune_formato_numerico", sa.Integer(), nullable=True),
        sa.Column("codice_comune_numerico_2017_2025", sa.Integer(), nullable=True),
        sa.Column("nome_comune_legacy", sa.String(length=100), nullable=True),
        sa.Column("cod_provincia", sa.Integer(), nullable=True),
        sa.Column("sigla_provincia", sa.String(length=2), nullable=True),
        sa.Column("regione", sa.String(length=100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("codice_catastale"),
        sa.UniqueConstraint("cod_comune_capacitas"),
    )
    op.create_index("ix_cat_comuni_codice_catastale", "cat_comuni", ["codice_catastale"], unique=True)
    op.create_index("ix_cat_comuni_cod_comune_capacitas", "cat_comuni", ["cod_comune_capacitas"], unique=True)

    comuni_table = sa.table(
        "cat_comuni",
        sa.column("nome_comune", sa.String),
        sa.column("codice_catastale", sa.String),
        sa.column("cod_comune_capacitas", sa.Integer),
        sa.column("codice_comune_formato_numerico", sa.Integer),
        sa.column("codice_comune_numerico_2017_2025", sa.Integer),
        sa.column("nome_comune_legacy", sa.String),
        sa.column("cod_provincia", sa.Integer),
        sa.column("sigla_provincia", sa.String),
        sa.column("regione", sa.String),
    )
    op.bulk_insert(
        comuni_table,
        [
            {
                "nome_comune": row[1],
                "codice_catastale": row[2],
                "cod_comune_capacitas": row[0],
                "codice_comune_formato_numerico": row[3],
                "codice_comune_numerico_2017_2025": row[4],
                "nome_comune_legacy": row[5],
                "cod_provincia": row[6],
                "sigla_provincia": row[7],
                "regione": row[8],
            }
            for row in COMUNI_ROWS
        ],
    )

    op.alter_column("cat_particelle", "cod_comune_istat", new_column_name="cod_comune_capacitas")
    op.alter_column("cat_particelle_history", "cod_comune_istat", new_column_name="cod_comune_capacitas")
    op.alter_column("cat_utenze_irrigue", "cod_comune_istat", new_column_name="cod_comune_capacitas")

    op.add_column("cat_particelle", sa.Column("comune_id", sa.Uuid(), nullable=True))
    op.add_column("cat_particelle", sa.Column("codice_catastale", sa.String(length=4), nullable=True))
    op.add_column("cat_particelle_history", sa.Column("comune_id", sa.Uuid(), nullable=True))
    op.add_column("cat_particelle_history", sa.Column("codice_catastale", sa.String(length=4), nullable=True))
    op.add_column("cat_utenze_irrigue", sa.Column("comune_id", sa.Uuid(), nullable=True))

    op.create_index("ix_cat_particelle_comune_id", "cat_particelle", ["comune_id"], unique=False)
    op.create_index("ix_cat_particelle_codice_catastale", "cat_particelle", ["codice_catastale"], unique=False)
    op.create_index("ix_cat_particelle_history_comune_id", "cat_particelle_history", ["comune_id"], unique=False)
    op.create_index("ix_cat_particelle_history_codice_catastale", "cat_particelle_history", ["codice_catastale"], unique=False)
    op.create_index("ix_cat_utenze_irrigue_comune_id", "cat_utenze_irrigue", ["comune_id"], unique=False)

    op.create_foreign_key("fk_cat_particelle_comune_id", "cat_particelle", "cat_comuni", ["comune_id"], ["id"])
    op.create_foreign_key("fk_cat_particelle_history_comune_id", "cat_particelle_history", "cat_comuni", ["comune_id"], ["id"])
    op.create_foreign_key("fk_cat_utenze_irrigue_comune_id", "cat_utenze_irrigue", "cat_comuni", ["comune_id"], ["id"])

    op.execute(
        """
        UPDATE cat_particelle p
        SET comune_id = c.id,
            codice_catastale = c.codice_catastale
        FROM cat_comuni c
        WHERE c.cod_comune_capacitas = p.cod_comune_capacitas
        """
    )
    op.execute(
        """
        UPDATE cat_particelle_history p
        SET comune_id = c.id,
            codice_catastale = c.codice_catastale
        FROM cat_comuni c
        WHERE c.cod_comune_capacitas = p.cod_comune_capacitas
        """
    )
    op.execute(
        """
        UPDATE cat_utenze_irrigue u
        SET comune_id = c.id
        FROM cat_comuni c
        WHERE c.cod_comune_capacitas = u.cod_comune_capacitas
        """
    )


def downgrade() -> None:
    op.execute("ALTER TABLE cat_utenze_irrigue DROP CONSTRAINT IF EXISTS fk_cat_utenze_irrigue_comune_id")
    op.execute("ALTER TABLE cat_particelle_history DROP CONSTRAINT IF EXISTS fk_cat_particelle_history_comune_id")
    op.execute("ALTER TABLE cat_particelle DROP CONSTRAINT IF EXISTS fk_cat_particelle_comune_id")

    op.drop_index("ix_cat_utenze_irrigue_comune_id", table_name="cat_utenze_irrigue")
    op.drop_index("ix_cat_particelle_history_codice_catastale", table_name="cat_particelle_history")
    op.drop_index("ix_cat_particelle_history_comune_id", table_name="cat_particelle_history")
    op.drop_index("ix_cat_particelle_codice_catastale", table_name="cat_particelle")
    op.drop_index("ix_cat_particelle_comune_id", table_name="cat_particelle")

    op.drop_column("cat_utenze_irrigue", "comune_id")
    op.drop_column("cat_particelle_history", "codice_catastale")
    op.drop_column("cat_particelle_history", "comune_id")
    op.drop_column("cat_particelle", "codice_catastale")
    op.drop_column("cat_particelle", "comune_id")

    op.alter_column("cat_utenze_irrigue", "cod_comune_capacitas", new_column_name="cod_comune_istat")
    op.alter_column("cat_particelle_history", "cod_comune_capacitas", new_column_name="cod_comune_istat")
    op.alter_column("cat_particelle", "cod_comune_capacitas", new_column_name="cod_comune_istat")

    op.drop_index("ix_cat_comuni_cod_comune_capacitas", table_name="cat_comuni")
    op.drop_index("ix_cat_comuni_codice_catastale", table_name="cat_comuni")
    op.drop_table("cat_comuni")
