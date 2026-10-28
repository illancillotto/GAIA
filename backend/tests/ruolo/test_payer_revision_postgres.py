"""A reassignment cannot leave a notice addressed to the previous payer confirmable."""

from pathlib import Path

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from app.modules.ruolo.notice_confirmation_models import NoticeGenerationConfirmation
from app.modules.ruolo.services import payer_assignments
from app.modules.ruolo.services.notice_draft_review import confirm_generation
from app.modules.ruolo.services.notice_revision import GenerationRevisionChanged, read_revision
from app.modules.utenze.models import AnagraficaPerson, AnagraficaSubject

from .test_notice_draft_inputs import _generate
from .test_notice_revision import generation_engine as generation_engine
from .test_notice_revision import real_revision_engine as real_revision_engine


def _migration():
    return load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20261028_0900_payer_assignment_notice_revision.py",
    )


def test_changing_payer_blocks_confirmation_of_a_prepared_notice(
    real_revision_engine, tmp_path, monkeypatch
):
    engine = real_revision_engine
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        _migration().upgrade()
    with Session(engine) as db, db.begin():
        subject = AnagraficaSubject(source_name_raw="PAGATORE TEST")
        db.add(subject)
        db.flush()
        db.add(
            AnagraficaPerson(
                subject_id=subject.id,
                cognome="PAGATORE",
                nome="TEST",
                codice_fiscale="VRDLGI80A01H501Z",
            )
        )
    identifier, avviso_id, _, _ = _generate(engine, tmp_path, monkeypatch, batch=True)
    with Session(engine) as db, db.begin():
        payer_assignments.assign(
            db,
            avviso_id=avviso_id,
            payer_tax_code="VRDLGI80A01H501Z",
            reason="ufficio",
            notes=None,
            user_id=1,
        )
    with Session(engine) as db, db.begin():
        with pytest.raises(GenerationRevisionChanged):
            confirm_generation(db, identifier, batch=True, actor_id=1)
    with Session(engine) as db:
        assert db.scalar(select(NoticeGenerationConfirmation)) is None
    for statement in (
        "UPDATE ruolo_tributi_payer_assignments SET notes = 'rettifica'",
        "DELETE FROM ruolo_tributi_payer_assignments",
        "TRUNCATE ruolo_tributi_payer_assignments",
    ):
        with engine.begin() as connection:
            before = read_revision(connection)
        with engine.begin() as connection:
            connection.execute(text("SET LOCAL session_replication_role = replica"))
            connection.execute(text(statement))
        with engine.begin() as connection:
            assert read_revision(connection).revision == before.revision + 1
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        _migration().downgrade()
        assert (
            connection.scalar(
                text(
                    "SELECT count(*) FROM pg_trigger WHERE tgrelid = 'ruolo_tributi_payer_assignments'::regclass AND NOT tgisinternal"
                )
            )
            == 0
        )


def test_assignment_revision_migration_is_a_noop_on_sqlite():
    engine = create_engine("sqlite://")
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        _migration().upgrade()
        _migration().downgrade()
        assert connection.scalar(text("SELECT count(*) FROM sqlite_master")) == 0
    engine.dispose()
