from pathlib import Path

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import inspect

from app.modules.ruolo.notice_confirmation_models import (
    NoticeExportClaim,
    NoticeExportIdentity,
    NoticeGenerationExport,
)

from .test_notice_generation_concurrency import _metadata
from .test_notice_generation_concurrency import generation_engine as generation_engine


def test_export_migration_matches_models_and_roundtrips(generation_engine):
    migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20260922_1000_notice_generation_exports.py",
    )
    with generation_engine.begin() as connection:
        NoticeExportClaim.__table__.drop(connection)
        NoticeExportIdentity.__table__.drop(connection)
        NoticeGenerationExport.__table__.drop(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
            for model in (NoticeGenerationExport, NoticeExportClaim, NoticeExportIdentity):
                assert {
                    column["name"]
                    for column in inspect(connection).get_columns(model.__tablename__)
                } == set(model.__table__.columns.keys())
            assert compare_metadata(MigrationContext.configure(connection), _metadata()) == []
            migration.downgrade()
            assert NoticeGenerationExport.__tablename__ not in inspect(connection).get_table_names()
            migration.upgrade()
