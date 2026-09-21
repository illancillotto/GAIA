from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import Column, Integer, MetaData, Table, create_engine, inspect, select

from app.modules.ruolo.notice_confirmation_models import NoticeGenerationConfirmation

from .test_notice_generation_concurrency import generation_engine as generation_engine


def test_confirmation_migration_roundtrip_preserves_existing_user():
    engine = create_engine("sqlite://")
    metadata = MetaData()
    users = Table("application_users", metadata, Column("id", Integer, primary_key=True))
    metadata.create_all(engine)
    migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20260921_2000_notice_generation_confirmation.py",
    )
    with engine.begin() as connection:
        connection.execute(users.insert().values(id=1))
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert "ruolo_notice_generation_confirmations" in inspect(connection).get_table_names()
            migration.downgrade()
            assert (
                "ruolo_notice_generation_confirmations" not in inspect(connection).get_table_names()
            )
            migration.upgrade()
            assert connection.scalar(select(users.c.id)) == 1
    engine.dispose()


def test_postgres_confirmation_migration_roundtrip(generation_engine):
    migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20260921_2000_notice_generation_confirmation.py",
    )
    with generation_engine.begin() as connection:
        NoticeGenerationConfirmation.__table__.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            columns = {
                column["name"]
                for column in inspect(connection).get_columns(
                    "ruolo_notice_generation_confirmations"
                )
            }
            assert columns == set(NoticeGenerationConfirmation.__table__.columns.keys())
            migration.downgrade()
            migration.upgrade()
