from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import inspect

from app.modules.ruolo.poste_dispatch_models import (
    PosteDispatchEvent,
    PosteDispatchItem,
    PosteDispatchLot,
)

from .poste_dispatch_fixtures import dispatch_engine, dispatch_metadata

MODELS = (PosteDispatchEvent, PosteDispatchItem, PosteDispatchLot)


def test_outbox_migration_matches_models_and_roundtrips():
    migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20261028_1500_poste_dispatch_outbox.py",
    )
    engine = dispatch_engine()
    with engine.begin() as connection:
        for model in MODELS:
            model.__table__.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            assert (
                compare_metadata(MigrationContext.configure(connection), dispatch_metadata()) == []
            )
            migration.downgrade()
            assert not {model.__tablename__ for model in MODELS} & set(
                inspect(connection).get_table_names()
            )
    engine.dispose()
