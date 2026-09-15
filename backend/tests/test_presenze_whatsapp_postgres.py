"""Integration checks restricted to an explicitly provided disposable PostgreSQL."""

import os
import runpy
from datetime import UTC, date, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.modules.presenze.services import punch_reminder_job as job
from app.modules.presenze.services.punch_reminder_pending import blocked_days, link_attempt
from app.modules.presenze.services.whatsapp_receipts import matching_receipts, store_receipt
from app.modules.presenze.services.whatsapp_waha import WhatsAppAck
from app.modules.presenze.whatsapp_models import PresenzeWhatsAppMessage

pytestmark = pytest.mark.postgres


@pytest.fixture
def pg_engine():
    url = os.environ.get("TEST_WHATSAPP_POSTGRES_URL")
    if not url:
        pytest.skip("TEST_WHATSAPP_POSTGRES_URL requires a disposable PostgreSQL")
    root = create_engine(url)
    schema = "whatsapp_test_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"}, pool_size=4)
    try:
        yield engine
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def test_postgres_lock_survives_app_commits_and_releases_on_exception(pg_engine):
    with Session(pg_engine) as db, Session(pg_engine) as competitor:
        with pytest.raises(RuntimeError, match="crash"):
            with job._advisory_lock(db) as acquired:
                assert acquired
                for _ in range(3):
                    db.execute(text("SELECT 1"))
                    db.commit()
                    with job._advisory_lock(competitor) as second:
                        assert not second
                raise RuntimeError("crash")
        with job._advisory_lock(competitor) as acquired:
            assert acquired
        with job._advisory_lock(db) as acquired:
            assert acquired


def migrations():
    directory = Path(__file__).parents[1] / "alembic" / "versions"
    return [
        runpy.run_path(str(directory / name))
        for name in [
            "20260915_1200_presenze_whatsapp_reminders.py",
            "20260915_1300_presenze_whatsapp_pending.py",
            "20260915_1400_presenze_whatsapp_config.py",
        ]
    ]


def test_migrations_and_persistence_on_postgres(pg_engine):
    revisions = migrations()
    collaborator_id = uuid4()
    with pg_engine.begin() as connection:
        connection.execute(text("CREATE TABLE application_users (id integer PRIMARY KEY)"))
        connection.execute(text("CREATE TABLE presenze_collaborators (id uuid PRIMARY KEY)"))
        connection.execute(
            text("INSERT INTO presenze_collaborators VALUES (:id)"), {"id": collaborator_id}
        )
        with Operations.context(MigrationContext.configure(connection)):
            for revision in revisions:
                revision["upgrade"]()
    with Session(pg_engine) as db:
        message = PresenzeWhatsAppMessage(
            collaborator_id=collaborator_id,
            phone_e164="+393330000001",
            text_body="test",
            days_json=[{"work_date": "2026-09-14", "problem": "missing_exit", "detail": "test"}],
            status="SENDING",
            provider="waha",
            provider_message_id="pg-id",
        )
        db.add(message)
        db.flush()
        link_attempt(db, message)
        link_attempt(db, message)
        db.commit()
        assert blocked_days(db) == {(collaborator_id, date(2026, 9, 14))}
        store_receipt(db, WhatsAppAck("pg-id", "READ"), datetime.now(UTC))
        store_receipt(db, WhatsAppAck("pg-id", "FAILED"), datetime.now(UTC))
        assert matching_receipts(db)[0].status == "READ"
        job.replay_receipts(db)
        db.commit()
        assert db.scalar(select(PresenzeWhatsAppMessage)).status == "READ"
        assert job.load_notified_days(db, date.min) == {(collaborator_id, date(2026, 9, 14))}
        job._mark_notified(db, message)
        db.commit()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(
                text("""INSERT INTO presenze_whatsapp_notified_days
                (id, kind, collaborator_id, work_date, problem, message_id)
                VALUES (:id, 'punch_reminder', :collaborator, '2026-09-14', 'missing_exit', :message)
            """),
                {"id": uuid4(), "collaborator": collaborator_id, "message": message.id},
            )
        db.rollback()
        with pytest.raises(IntegrityError), db.begin_nested():
            db.execute(text("INSERT INTO presenze_whatsapp_config (id) VALUES (2)"))
        db.rollback()
    with pg_engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            for revision in reversed(revisions):
                revision["downgrade"]()
            for revision in revisions:
                revision["upgrade"]()
        assert (
            connection.execute(text("SELECT count(*) FROM presenze_whatsapp_pending_days")).scalar()
            == 0
        )
