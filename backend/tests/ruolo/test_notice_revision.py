"""Real PostgreSQL commit fences; these are not end-to-end confirmation tests."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from queue import Queue
from time import monotonic
from uuid import uuid4

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import MetaData, create_engine, select, text
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.modules.ruolo import tributi_repositories as repo
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiYearManager
from app.modules.ruolo.notice_register_models import NoticeDocument
from app.modules.ruolo.notice_register_schemas import HistoricalDocument, OperatorChange
from app.modules.ruolo.notice_revision_models import NoticeGenerationRevision
from app.modules.ruolo.services import notice_register
from app.modules.ruolo.services.notice_revision import (
    DEPENDENCY_TABLES,
    GenerationRevisionChanged,
    RevisionProtocolUnavailable,
    lock_revision,
    read_revision,
)
from app.modules.utenze.models import AnagraficaPaymentNotice

from .test_notice_generation_concurrency import (
    _change_eligibility,
    _seed,
    generation_engine,  # noqa: F401 - shared isolated PostgreSQL fixture
)


def _migration():
    return load_python_file(
        str(Path(__file__).parents[2] / "alembic" / "versions"),
        "20260921_1700_notice_generation_revision.py",
    )


def _upgrade(engine):
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        _migration().upgrade()


@pytest.fixture
def revision_engine():
    """Minimal rows isolate trigger behavior from unrelated business constraints."""
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip(
            "GAIA_TEST_POSTGRES_URL richiesto; nessuna simulazione SQLite della concorrenza"
        )
    admin = create_engine(url)
    assert admin.dialect.name == "postgresql"
    schema = f"notice_revision_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(
        url,
        connect_args={
            "options": f"-csearch_path={schema} -clock_timeout=5000 -cstatement_timeout=10000"
        },
    )
    try:
        with engine.begin() as connection:
            for table in DEPENDENCY_TABLES:
                connection.execute(
                    text(f"CREATE TABLE {table} (id integer PRIMARY KEY, value text)")
                )
        _upgrade(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


@pytest.fixture
def real_revision_engine(request):
    engine = request.getfixturevalue("generation_engine")
    NoticeGenerationRevision.__table__.drop(engine)
    _upgrade(engine)
    return engine


def _current(engine):
    with engine.begin() as connection:
        return read_revision(connection)


def _assert_stale(engine, token):
    with engine.begin() as connection, pytest.raises(GenerationRevisionChanged):
        lock_revision(connection, token)


@pytest.mark.parametrize("table", sorted(DEPENDENCY_TABLES))
@pytest.mark.parametrize("operation", ["insert", "update", "delete", "truncate"])
def test_every_dependency_raw_sql(revision_engine, table, operation):
    with revision_engine.begin() as connection:
        connection.execute(text(f"INSERT INTO {table} VALUES (1, 'before')"))
    before = _current(revision_engine)
    statements = {
        "insert": f"INSERT INTO {table} VALUES (2, 'after')",
        "update": f"UPDATE {table} SET value = 'after' WHERE id = 1",
        "delete": f"DELETE FROM {table} WHERE id = 1",
        "truncate": f"TRUNCATE {table}",
    }
    with revision_engine.begin() as writer:
        writer.execute(text(statements[operation]))
        assert _current(revision_engine) == before
    after = _current(revision_engine)
    assert after.epoch == before.epoch
    assert after.revision == before.revision + 1
    _assert_stale(revision_engine, before)


def test_copy_bulk_replica_and_one_revision_per_transaction(revision_engine):
    before = _current(revision_engine)
    with revision_engine.begin() as writer:
        writer.execute(text("SET LOCAL session_replication_role = replica"))
        with writer.connection.driver_connection.cursor() as cursor:
            with cursor.copy("COPY ruolo_tributi_payments (id, value) FROM STDIN WITH CSV") as copy:
                copy.write("1,first\n2,second\n3,third\n")
        writer.execute(text("UPDATE ruolo_tributi_payments SET value = 'changed'"))
        writer.execute(text("INSERT INTO ana_payment_notices VALUES (1, 'inCASS')"))
        assert _current(revision_engine) == before
    assert _current(revision_engine).revision == before.revision + 1


def test_rollback_savepoint_and_noop_do_not_invalidate(revision_engine):
    before = _current(revision_engine)
    with revision_engine.connect() as writer:
        writer.execute(text("INSERT INTO ruolo_tributi_payments VALUES (1, 'rollback')"))
        writer.rollback()
        with writer.begin():
            nested = writer.begin_nested()
            writer.execute(text("INSERT INTO ruolo_tributi_payments VALUES (2, 'savepoint')"))
            nested.rollback()
            writer.execute(text("DELETE FROM ruolo_tributi_payments WHERE id = 999"))
    assert _current(revision_engine) == before
    with revision_engine.begin() as connection:
        assert lock_revision(connection, before) == before


def test_revision_singleton_missing_rejects_reader_and_writer(revision_engine):
    with revision_engine.begin() as connection:
        connection.execute(text("DELETE FROM ruolo_notice_generation_revision"))
    with revision_engine.begin() as connection, pytest.raises(RevisionProtocolUnavailable):
        read_revision(connection)
    with pytest.raises(DBAPIError, match="Notice generation revision is missing"):
        with revision_engine.begin() as writer:
            writer.execute(text("INSERT INTO ruolo_avvisi VALUES (1, 'must roll back')"))
    with revision_engine.connect() as connection:
        assert connection.scalar(text("SELECT count(*) FROM ruolo_avvisi")) == 0


@pytest.mark.parametrize(
    "statement",
    [
        "ALTER TABLE ruolo_avvisi DISABLE TRIGGER gaia_notice_revision_row",
        "ALTER TABLE ruolo_avvisi ENABLE TRIGGER gaia_notice_revision_row",
        "ALTER TABLE ruolo_avvisi DISABLE TRIGGER gaia_notice_revision_truncate",
        "DROP TRIGGER gaia_notice_revision_row ON ana_payment_notices",
        "DROP TRIGGER gaia_notice_revision_truncate ON ruolo_notice_positions",
    ],
)
def test_incomplete_enforcement_is_refused(revision_engine, statement):
    before = _current(revision_engine)
    with revision_engine.begin() as connection:
        connection.execute(text(statement))
    with revision_engine.begin() as connection, pytest.raises(RevisionProtocolUnavailable):
        lock_revision(connection, before)


@pytest.mark.parametrize("isolation", ["AUTOCOMMIT", "REPEATABLE READ", "SERIALIZABLE"])
def test_incompatible_isolation_is_refused(revision_engine, isolation):
    with revision_engine.connect().execution_options(isolation_level=isolation) as connection:
        with pytest.raises(RevisionProtocolUnavailable, match="READ COMMITTED"):
            read_revision(connection)


def test_engine_default_autocommit_is_refused(revision_engine):
    engine = create_engine(revision_engine.url, isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as connection:
            # SQLAlchemy reports READ COMMITTED even when DBAPI autocommit is on.
            assert connection.get_isolation_level() == "READ COMMITTED"
            with pytest.raises(RevisionProtocolUnavailable, match="senza autocommit"):
                read_revision(connection)
    finally:
        engine.dispose()


def test_migration_sqlite_is_metadata_only():
    engine = create_engine("sqlite://")
    with engine.begin() as connection, Operations.context(MigrationContext.configure(connection)):
        migration = _migration()
        migration.upgrade()
        assert connection.scalar(text("SELECT count(*) FROM ruolo_notice_generation_revision")) == 0
        with pytest.raises(RevisionProtocolUnavailable, match="PostgreSQL"):
            read_revision(connection)
        migration.downgrade()
        migration.upgrade()
    engine.dispose()


def test_migration_parity_roundtrip_and_new_epoch(real_revision_engine):
    migration = _migration()
    assert set(migration.DEPENDENCY_TABLES) == DEPENDENCY_TABLES
    before = _current(real_revision_engine)
    assert before.revision == 0
    with real_revision_engine.begin() as connection:
        metadata = MetaData()
        NoticeGenerationRevision.__table__.to_metadata(metadata)
        metadata.reflect(connection, extend_existing=False)
        context = MigrationContext.configure(connection)
        assert compare_metadata(context, metadata) == []
        with Operations.context(context):
            migration.downgrade()
            migration.upgrade()
    after = _current(real_revision_engine)
    assert after.revision == 0
    assert after.epoch != before.epoch
    _assert_stale(real_revision_engine, before)


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO ruolo_notice_generation_revision (id, epoch) SELECT 2, epoch FROM ruolo_notice_generation_revision",
        "UPDATE ruolo_notice_generation_revision SET revision = -1",
    ],
)
def test_revision_constraints(revision_engine, statement):
    with revision_engine.begin() as connection, pytest.raises(IntegrityError):
        connection.execute(text(statement))


def _await_blocked(observer, waiter, holder):
    deadline = monotonic() + 4
    while monotonic() < deadline:
        blocked = observer.scalar(
            text("""
                WITH RECURSIVE blockers(pid) AS (
                    SELECT unnest(pg_blocking_pids(:waiter))
                    UNION
                    SELECT unnest(pg_blocking_pids(pid)) FROM blockers
                )
                SELECT EXISTS (SELECT 1 FROM blockers WHERE pid = :holder)
            """),
            {"waiter": waiter, "holder": holder},
        )
        if blocked:
            return
    pytest.fail("Il worker non ha raggiunto il lock PostgreSQL atteso")


def _writer(engine, queue, identifier):
    with engine.begin() as writer:
        writer.execute(
            text("INSERT INTO ruolo_tributi_payments VALUES (:id, 'payment')"), {"id": identifier}
        )
        queue.put(writer.scalar(text("SELECT pg_backend_pid()")))


def test_fence_blocks_commits_not_rendering_and_later_invalidates(revision_engine):
    token = _current(revision_engine)
    ready = Queue()
    with ThreadPoolExecutor(max_workers=2) as pool, revision_engine.connect() as fence:
        lock_revision(fence, token)
        holder = fence.scalar(text("SELECT pg_backend_pid()"))
        futures = [
            pool.submit(_writer, revision_engine, ready, identifier) for identifier in (1, 2)
        ]
        try:
            # Both writes finish before waiting on commit. No timing-based sleeps.
            with revision_engine.connect() as observer:
                for _ in futures:
                    _await_blocked(observer, ready.get(timeout=4), holder)
            assert read_revision(fence) == token
        finally:
            fence.commit()
        for future in futures:
            future.result(timeout=5)
    assert _current(revision_engine).revision == token.revision + 2
    _assert_stale(revision_engine, token)


def _lock_worker(engine, token, queue):
    with engine.begin() as connection:
        queue.put(connection.scalar(text("SELECT pg_backend_pid()")))
        return lock_revision(connection, token)


@pytest.mark.parametrize("commit_writer", [True, False])
def test_prior_writer_commit_or_rollback_is_observed(revision_engine, commit_writer):
    token = _current(revision_engine)
    ready = Queue()
    with ThreadPoolExecutor(max_workers=1) as pool, revision_engine.connect() as writer:
        writer.execute(text("INSERT INTO ruolo_notice_documents VALUES (1, 'orphan')"))
        writer.execute(text("SET CONSTRAINTS ALL IMMEDIATE"))
        holder = writer.scalar(text("SELECT pg_backend_pid()"))
        future = pool.submit(_lock_worker, revision_engine, token, ready)
        try:
            with revision_engine.connect() as observer:
                _await_blocked(observer, ready.get(timeout=4), holder)
        finally:
            writer.commit() if commit_writer else writer.rollback()
        if commit_writer:
            with pytest.raises(GenerationRevisionChanged):
                future.result(timeout=5)
        else:
            assert future.result(timeout=5) == token


def test_uncommitted_writer_does_not_lock_read_or_render(revision_engine):
    token = _current(revision_engine)
    with revision_engine.begin() as writer:
        writer.execute(text("INSERT INTO ruolo_tributi_payments VALUES (1, 'pending')"))
        with revision_engine.begin() as rendering:
            assert lock_revision(rendering, token) == token
    _assert_stale(revision_engine, token)


def test_lock_timeout_rolls_back_without_changing_revision(revision_engine):
    token = _current(revision_engine)
    with revision_engine.begin() as holder:
        lock_revision(holder, token)
        with pytest.raises(DBAPIError, match="lock timeout"):
            with revision_engine.begin() as contender:
                contender.execute(text("SET LOCAL lock_timeout = '20ms'"))
                lock_revision(contender, token)
    with revision_engine.begin() as connection:
        assert lock_revision(connection, token) == token


@pytest.mark.parametrize("tax_year", [2022, 2023])
@pytest.mark.parametrize("change_kind", ["payment", "notification", "step"])
def test_real_domain_writers_advance_revision(
    real_revision_engine, tmp_path, tax_year, change_kind
):
    avviso_id, document_id = _seed(real_revision_engine, tmp_path, tax_year)
    token = _current(real_revision_engine)
    _change_eligibility(real_revision_engine, avviso_id, document_id, change_kind)
    assert _current(real_revision_engine).revision == token.revision + 1
    _assert_stale(real_revision_engine, token)


@pytest.mark.parametrize("change_kind", ["partial_payment", "orphan", "incass", "policy", "unlink"])
def test_real_additional_dependencies(real_revision_engine, tmp_path, change_kind):
    avviso_id, _ = _seed(real_revision_engine, tmp_path, 2022)
    token = _current(real_revision_engine)
    with Session(real_revision_engine) as db:
        avviso = db.get(RuoloAvviso, avviso_id)
        if change_kind == "partial_payment":
            repo.create_payment(db, avviso=avviso, amount=25, created_by=1)
        elif change_kind == "orphan":
            notice_register.create_historical_document(
                db,
                HistoricalDocument(document_number="ORPHAN", tax_code=avviso.codice_fiscale_raw),
                OperatorChange(actor_id=1, reason="Storico non collegato", expected_version=1),
            )
        elif change_kind == "incass":
            db.add(AnagraficaPaymentNotice(source_notice_id="new-incass", anno="2022"))
        elif change_kind == "policy":
            db.add(
                RuoloTributiYearManager(
                    year_from=2022,
                    manager_key="test",
                    manager_label="Test",
                    calculation_policy="internal_gaia",
                )
            )
        else:
            db.execute(text("UPDATE ruolo_notice_positions SET avviso_id = NULL"))
        db.commit()
    assert _current(real_revision_engine).revision == token.revision + 1
    _assert_stale(real_revision_engine, token)
    if change_kind == "partial_payment":
        with Session(real_revision_engine) as db:
            item = repo.get_tributi_avviso(db, avviso_id)
            assert item["reminder_enabled"]
            assert item["saldo_amount"] == 75


def test_read_bypasses_stale_orm_identity(real_revision_engine, tmp_path):
    avviso_id, document_id = _seed(real_revision_engine, tmp_path, 2023)
    with Session(real_revision_engine) as db:
        document = db.get(NoticeDocument, document_id)
        original_version = document.version
        token = read_revision(db.connection())
        _change_eligibility(real_revision_engine, avviso_id, document_id, "notification")
        assert db.scalar(select(NoticeDocument)) is document
        assert document.version == original_version
        with pytest.raises(GenerationRevisionChanged):
            lock_revision(db.connection(), token)
