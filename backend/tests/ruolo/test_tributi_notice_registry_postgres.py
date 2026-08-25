from __future__ import annotations

import multiprocessing
import os
import threading
import uuid
from collections.abc import Callable, Iterator
from concurrent.futures import ThreadPoolExecutor
from queue import Empty
from typing import Any

import pytest
from sqlalchemy import (
    Column,
    Integer,
    MetaData,
    Table,
    Uuid,
    create_engine,
    select,
    text,
)
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from app.modules.ruolo.models import (
    RuoloTributiNoticeNumber,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.services import tributi_notice_registry as notice_registry

pytestmark = pytest.mark.postgres

SessionFactory = sessionmaker[Session]


def _candidate(index: int = 0) -> dict[str, object]:
    return {
        "codice_fiscale": f"RSSMRA80A01H{index:04d}",
        "avvisi": [{"id": f"avviso-{index}"}],
    }


def _create_registry_tables(engine: Engine) -> None:
    metadata = MetaData()
    Table("application_users", metadata, Column("id", Integer, primary_key=True))
    Table("ana_subjects", metadata, Column("id", Uuid, primary_key=True))
    RuoloTributiReminderBatch.__table__.to_metadata(metadata)
    RuoloTributiNoticeNumber.__table__.to_metadata(metadata)
    RuoloTributiReminderBatchItem.__table__.to_metadata(metadata)
    metadata.create_all(engine)


@pytest.fixture(scope="module")
def postgres_session_factory() -> Iterator[SessionFactory]:
    database_url = os.getenv("GAIA_TEST_POSTGRES_URL", "").strip()
    if not database_url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")

    schema = f"test_notice_registry_{uuid.uuid4().hex}"
    admin_engine = create_engine(database_url, pool_pre_ping=True)
    if admin_engine.dialect.name != "postgresql":
        admin_engine.dispose()
        pytest.skip("GAIA_TEST_POSTGRES_URL deve puntare a PostgreSQL")

    engine: Engine | None = None
    schema_created = False
    try:
        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        schema_created = True
        engine = create_engine(
            database_url,
            pool_size=12,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={"options": f"-csearch_path={schema},public"},
        )
        _create_registry_tables(engine)
    except SQLAlchemyError as exc:
        if engine is not None:
            engine.dispose()
        if schema_created:
            with admin_engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()
        if isinstance(exc, OperationalError):
            pytest.skip(f"PostgreSQL di test non disponibile: {exc}")
        raise

    try:
        yield sessionmaker(bind=engine, expire_on_commit=False)
    finally:
        engine.dispose()
        with admin_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin_engine.dispose()


@pytest.fixture(autouse=True)
def empty_registry(postgres_session_factory: SessionFactory) -> Iterator[None]:
    bind = postgres_session_factory.kw["bind"]
    with bind.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE TABLE ruolo_tributi_reminder_batch_items, "
                "ruolo_tributi_reminder_batches, ruolo_tributi_notice_numbers CASCADE"
            )
        )
    yield


def _synchronise_initial_progressive_reads(
    monkeypatch: pytest.MonkeyPatch,
    participant_count: int,
) -> None:
    barrier = threading.Barrier(participant_count, timeout=15)
    original = notice_registry.next_notice_progressive
    first_call_by_thread: set[int] = set()
    lock = threading.Lock()

    def synchronised(db: Session, *, emission_year: int) -> int:
        progressive = original(db, emission_year=emission_year)
        thread_id = threading.get_ident()
        with lock:
            is_first_call = thread_id not in first_call_by_thread
            first_call_by_thread.add(thread_id)
        if is_first_call:
            barrier.wait()
        return progressive

    monkeypatch.setattr(notice_registry, "next_notice_progressive", synchronised)


def _reserve_and_commit(
    session_factory: SessionFactory,
    candidate: dict[str, object],
) -> tuple[uuid.UUID, int, str]:
    with session_factory() as db:
        reservation = notice_registry.reserve_notice_number(
            db,
            emission_year=2026,
            candidate=candidate,
            reference_years=[2025],
        )
        db.commit()
        return reservation.id, reservation.progressive, reservation.notice_number


def _process_reserve_and_commit(
    database_url: str,
    schema: str,
    candidate_index: int,
    barrier: Any,
    result_queue: Any,
) -> None:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        connect_args={"options": f"-csearch_path={schema},public"},
    )
    original = notice_registry.next_notice_progressive
    first_call = True

    def synchronised(db: Session, *, emission_year: int) -> int:
        nonlocal first_call
        progressive = original(db, emission_year=emission_year)
        if first_call:
            first_call = False
            barrier.wait(timeout=20)
        return progressive

    notice_registry.next_notice_progressive = synchronised
    try:
        factory = sessionmaker(bind=engine, expire_on_commit=False)
        result_queue.put(
            ("ok", _reserve_and_commit(factory, _candidate(candidate_index)))
        )
    except (SQLAlchemyError, RuntimeError, threading.BrokenBarrierError) as exc:
        result_queue.put(("error", repr(exc)))
    finally:
        engine.dispose()


def _run_concurrently(
    worker_count: int, operation: Callable[[int], object]
) -> list[object]:
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        return list(executor.map(operation, range(worker_count)))


def test_different_identities_survive_real_postgres_contention(
    postgres_session_factory: SessionFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_count = 8
    _synchronise_initial_progressive_reads(monkeypatch, worker_count)

    results = _run_concurrently(
        worker_count,
        lambda index: _reserve_and_commit(postgres_session_factory, _candidate(index)),
    )

    assert sorted(result[1] for result in results) == list(range(1, worker_count + 1))
    assert len({result[0] for result in results}) == worker_count
    assert len({result[2] for result in results}) == worker_count
    with postgres_session_factory() as db:
        persisted = db.scalars(
            select(RuoloTributiNoticeNumber).order_by(
                RuoloTributiNoticeNumber.progressive
            )
        ).all()
        assert [item.progressive for item in persisted] == list(
            range(1, worker_count + 1)
        )


def test_same_identity_is_idempotent_under_real_postgres_contention(
    postgres_session_factory: SessionFactory,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    worker_count = 6
    _synchronise_initial_progressive_reads(monkeypatch, worker_count)

    results = _run_concurrently(
        worker_count,
        lambda _index: _reserve_and_commit(postgres_session_factory, _candidate()),
    )

    assert len(set(results)) == 1
    assert results[0][1] == 1
    with postgres_session_factory() as db:
        assert len(db.scalars(select(RuoloTributiNoticeNumber)).all()) == 1


@pytest.mark.parametrize(
    ("candidate_indexes", "expected_progressives", "expected_persisted_count"),
    [
        pytest.param([0, 1, 2, 3], [1, 2, 3, 4], 4, id="different-identities"),
        pytest.param([0, 0, 0, 0], [1, 1, 1, 1], 1, id="same-identity"),
    ],
)
def test_separate_processes_survive_real_postgres_contention(
    postgres_session_factory: SessionFactory,
    candidate_indexes: list[int],
    expected_progressives: list[int],
    expected_persisted_count: int,
) -> None:
    process_count = len(candidate_indexes)
    bind = postgres_session_factory.kw["bind"]
    database_url = bind.url.render_as_string(hide_password=False)
    with postgres_session_factory() as db:
        schema = db.scalar(select(text("current_schema()")))
    assert isinstance(schema, str)

    context = multiprocessing.get_context("spawn")
    barrier = context.Barrier(process_count)
    result_queue = context.Queue()
    processes = [
        context.Process(
            target=_process_reserve_and_commit,
            args=(database_url, schema, index, barrier, result_queue),
        )
        for index in candidate_indexes
    ]
    for process in processes:
        process.start()
    for process in processes:
        process.join(timeout=30)
        if process.is_alive():
            process.terminate()
            process.join(timeout=5)

    results = []
    for _process in processes:
        try:
            results.append(result_queue.get(timeout=5))
        except Empty:
            results.append(("error", "worker terminato senza risultato"))

    assert [process.exitcode for process in processes] == [0] * process_count
    assert [status for status, _result in results] == ["ok"] * process_count
    reservations = [result for _status, result in results]
    assert sorted(result[1] for result in reservations) == expected_progressives
    assert len({result[0] for result in reservations}) == expected_persisted_count
    with postgres_session_factory() as db:
        assert (
            len(db.scalars(select(RuoloTributiNoticeNumber)).all())
            == expected_persisted_count
        )


def test_outer_transaction_rollback_releases_the_number_on_postgres(
    postgres_session_factory: SessionFactory,
) -> None:
    with postgres_session_factory() as db:
        rolled_back = notice_registry.reserve_notice_number(
            db,
            emission_year=2026,
            candidate=_candidate(),
            reference_years=[2025],
        )
        rolled_back_id = rolled_back.id
        db.rollback()

    committed = _reserve_and_commit(postgres_session_factory, _candidate(1))

    assert committed[1] == 1
    with postgres_session_factory() as db:
        assert db.get(RuoloTributiNoticeNumber, rolled_back_id) is None
        assert len(db.scalars(select(RuoloTributiNoticeNumber)).all()) == 1
