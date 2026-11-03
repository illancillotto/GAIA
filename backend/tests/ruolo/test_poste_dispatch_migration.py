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
    accounts = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20261103_0900_poste_dispatch_accounts.py",
    )
    engine = dispatch_engine()
    with engine.begin() as connection:
        for model in MODELS:
            model.__table__.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            accounts.upgrade()
            assert (
                compare_metadata(MigrationContext.configure(connection), dispatch_metadata()) == []
            )
            accounts.downgrade()
            migration.downgrade()
            assert not {model.__tablename__ for model in MODELS} & set(
                inspect(connection).get_table_names()
            )
    engine.dispose()


def test_account_migration_preserves_legacy_lots_without_guessing_the_account():
    from uuid import uuid4

    from sqlalchemy import text
    from sqlalchemy.orm import Session

    from .poste_dispatch_fixtures import seed_user

    root = str(Path(__file__).parents[2] / "alembic" / "versions")
    previous = load_python_file(root, "20261028_1500_poste_dispatch_outbox.py")
    migration = load_python_file(root, "20261103_0900_poste_dispatch_accounts.py")
    engine = dispatch_engine()
    with engine.connect() as connection:
        connection.execute(text("PRAGMA foreign_keys=OFF"))
        connection.commit()
        with connection.begin():
            for model in MODELS:
                model.__table__.drop(connection)
            with Operations.context(MigrationContext.configure(connection)):
                previous.upgrade()
                with Session(connection) as db:
                    seed_user(db)
                    db.flush()
                lot_id, event_id = uuid4().hex, uuid4().hex
                connection.execute(text("INSERT INTO ruolo_poste_dispatch_lots (id, title, status, postal_options, created_by) VALUES (:id, 'Storico', 'open', '{}', 1)"), {"id": lot_id})
                connection.execute(text("INSERT INTO ruolo_poste_dispatch_events (id, lot_id, kind, actor_id) VALUES (:id, :lot, 'lot_created', 1)"), {"id": event_id, "lot": lot_id})
                migration.upgrade()
                lot = connection.execute(text("SELECT credential_id, poste_username, created_by_username FROM ruolo_poste_dispatch_lots")).one()
                assert lot == (None, None, "poste-1")
                assert connection.scalar(text("SELECT actor_username FROM ruolo_poste_dispatch_events")) == "poste-1"
                migration.downgrade()
                assert connection.scalar(text("SELECT title FROM ruolo_poste_dispatch_lots")) == "Storico"
    engine.dispose()
