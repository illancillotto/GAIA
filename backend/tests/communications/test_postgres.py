"""Real PostgreSQL guarantees, isolated in a disposable schema and database."""

import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from ruolo.poste_dispatch_fixtures import seed_batch_item
from ruolo.test_notice_register_api import _seed_auth
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from app.modules.communications import models, outbox, queue, registry
from app.modules.communications.policy import account_fingerprint, sha256
from app.modules.ruolo.notice_revision_models import NoticeGenerationRevision
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.ruolo.services.notice_revision import DEPENDENCY_TABLES

from .conftest import account_input, metadata, pdf


def migration(name):
    folder = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    return load_python_file(str(folder), name)


@pytest.fixture
def postgres(tmp_path):
    url = os.getenv("COMMUNICATIONS_TEST_POSTGRES_URL")
    if not url:
        pytest.skip(
            "COMMUNICATIONS_TEST_POSTGRES_URL non configurato; nessuna simulazione dei lock PG"
        )
    admin = sa.create_engine(url)
    assert admin.dialect.name == "postgresql"
    assert sa.engine.make_url(url).database == "communications_test", (
        "Solo database isolato communications_test"
    )
    schema = f"comm_{uuid4().hex}"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = sa.create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    source = metadata()
    for table in list(source.tables.values()):
        if table.name.startswith("communication_"):
            source.remove(table)
    for name in DEPENDENCY_TABLES:
        if name not in source.tables:
            sa.Table(name, source, sa.Column("id", sa.Integer(), primary_key=True))
    try:
        source.create_all(engine)
        with engine.begin() as connection:
            _seed_auth(connection)
            with Operations.context(MigrationContext.configure(connection)):
                migration("20260921_1700_notice_generation_revision.py").upgrade()
                migration("20261103_1200_communications.py").upgrade()
        factory = sessionmaker(engine, autoflush=False, expire_on_commit=False)
        with factory() as db:
            batch_item = seed_batch_item(db, tmp_path, content=pdf())
            account = registry.save_account(db, account_input(), 1)
            from app.modules.ruolo.notice_register_models import NoticeDocument

            document = NoticeDocument(
                source_system="gaia_batch_item",
                source_key=str(batch_item.id),
                document_number=batch_item.payload_json["notice_number"],
                original_json={},
            )
            db.add(document)
            db.flush()
            message = models.CommunicationMessage(
                source_entity_id=batch_item.id,
                document_id=document.id,
                notice_number=document.document_number,
                channel="pec",
                account_id=account.id,
                account_digest=account_fingerprint(account),
                sender=account.sender,
                recipient="recipient@example.org",
                subject="Synthetic",
                body="Synthetic",
                source_digest="a" * 64,
                created_by=1,
                state="draft",
                version=1,
            )
            db.add(message)
            db.flush()
            db.add(
                models.CommunicationAttachment(
                    message_id=message.id,
                    filename="synthetic.pdf",
                    primary_document=True,
                    content=pdf(),
                    sha256=sha256(pdf()),
                    size=len(pdf()),
                    pages=3,
                )
            )
            db.commit()
            ids = (batch_item.id, account.id, message.id)
        yield engine, factory, ids
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


def test_migration_schema_seed_and_roundtrip(postgres):
    engine, _factory, _ = postgres
    expected = metadata()
    with engine.begin() as connection:

        def include(item, name, kind, reflected, other):
            return (
                name.startswith("communication_")
                if kind == "table"
                else item.table.name.startswith("communication_")
            )

        context = MigrationContext.configure(connection, opts={"include_object": include})
        assert compare_metadata(context, expected) == []
        templates = (
            connection.execute(sa.select(models.CommunicationTemplate.status)).scalars().all()
        )
        assert templates == ["draft", "draft"]
        assert connection.scalar(sa.select(models.CommunicationControl.paused))
    # Roundtrip on a fresh schema is covered separately: populated evidence must never be downgraded.


def test_mutex_is_session_scoped_released_on_error_and_not_shared(postgres):
    engine, _, (_, account_id, _) = postgres
    with pytest.raises(RuntimeError):
        with queue.account_mutex(engine, account_id) as acquired:
            assert acquired
            with queue.account_mutex(engine, account_id) as second:
                assert not second
            raise RuntimeError("synthetic interruption")
    with queue.account_mutex(engine, account_id) as reacquired:
        assert reacquired


def test_immutable_snapshots_and_append_only_audit(postgres):
    _, factory, (_, _account_id, message_id) = postgres
    with factory() as db:
        part = db.scalar(sa.select(models.CommunicationAttachment))
        audit = models.CommunicationEvent(aggregate_id=message_id, kind="synthetic", detail={})
        db.add(audit)
        db.commit()
        for table, identity, values in (
            (models.CommunicationAttachment, part.id, {"content": b"tampered"}),
            (models.CommunicationEvent, audit.id, {"kind": "tampered"}),
        ):
            with pytest.raises(sa.exc.DBAPIError):
                with db.begin_nested():
                    db.execute(sa.update(table).where(table.id == identity).values(**values))
            with pytest.raises(sa.exc.DBAPIError):
                with db.begin_nested():
                    db.execute(sa.delete(table).where(table.id == identity))


def test_cross_channel_race_has_exactly_one_reservation(postgres):
    _, factory, (batch_id, _, message_id) = postgres
    with factory() as db:
        lot = PosteDispatchLot(title="Synthetic", created_by=1, postal_options={})
        db.add(lot)
        db.commit()
        lot_id = lot.id
    barrier = Barrier(2)

    def reserve(channel):
        with factory() as db:
            barrier.wait(timeout=5)
            try:
                message = db.get(models.CommunicationMessage, message_id)
                if channel == "pec":
                    message.active_key, message.state = message.notice_number, "approved"
                else:
                    db.add(
                        PosteDispatchItem(
                            lot_id=lot_id,
                            batch_item_id=batch_id,
                            notice_number=message.notice_number,
                            shipment_name=f"GAIA {message.notice_number}",
                            active_key=f"GAIA {message.notice_number}",
                            active_source_key=str(batch_id),
                            status="address_pending",
                            recipient={},
                            artifact=pdf(),
                            artifact_sha256=sha256(pdf()),
                            artifact_size=len(pdf()),
                        )
                    )
                db.commit()
                return True
            except sa.exc.IntegrityError:
                db.rollback()
                return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(reserve, ("pec", "poste")))
    assert sorted(results) == [False, True]


def test_source_fence_and_job_claim_are_real_postgresql(postgres, monkeypatch):
    _, factory, (_, account_id, message_id) = postgres
    from app.modules.ruolo.notice_register_models import NoticeDocument

    with factory() as db:
        message = db.get(models.CommunicationMessage, message_id)
        document = db.get(NoticeDocument, message.document_id)
        monkeypatch.setattr(
            outbox.ruolo_source,
            "inspect",
            lambda *args, **kwargs: (None, document, pdf(), message.source_digest),
        )
        assert len(outbox.verify(db, message, 1)) == 1
        revision = db.get(NoticeGenerationRevision, 1)
        assert revision.revision > 0
        queue.control(db).paused = False
        message.state = "queued"
        job = models.CommunicationJob(
            message_id=message.id,
            account_id=account_id,
            kind="dispatch_pec",
            idempotency_key="synthetic-claim",
        )
        db.add(job)
        db.commit()
        first = queue.claim(db, account_id)
        assert first and queue.claim(db, account_id) is None


def test_migration_upgrade_downgrade_upgrade_empty(postgres):
    engine, _, _ = postgres
    # A separate empty namespace, preserving the populated schema used by the fixture.
    schema = f"roundtrip_{uuid4().hex}"
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
        original = connection.scalar(sa.text("SHOW search_path"))
        connection.execute(sa.text(f'SET LOCAL search_path = "{schema}"'))
        parent = metadata()
        for table in list(parent.tables.values()):
            if table.name.startswith("communication_"):
                parent.remove(table)
        for name in DEPENDENCY_TABLES:
            if name not in parent.tables:
                sa.Table(name, parent, sa.Column("id", sa.Integer(), primary_key=True))
        parent.create_all(connection)
        with Operations.context(MigrationContext.configure(connection)):
            migration("20260921_1700_notice_generation_revision.py").upgrade()
            current = migration("20261103_1200_communications.py")
            current.upgrade()
            current.downgrade()
            current.upgrade()
        assert (
            connection.scalar(sa.select(sa.func.count()).select_from(models.CommunicationTemplate))
            == 2
        )
        connection.execute(sa.text(f"SET LOCAL search_path = {original}"))
        connection.execute(DropSchema(schema, cascade=True))


def test_two_worker_instances_cannot_claim_the_same_account_at_once(postgres):
    from threading import Event

    engine, factory, (_, account_id, message_id) = postgres
    with factory() as db:
        queue.control(db).paused = False
        db.add(
            models.CommunicationJob(
                message_id=message_id,
                account_id=account_id,
                kind="dispatch_pec",
                idempotency_key="concurrent-worker",
            )
        )
        db.commit()
    entered, attempted = Event(), Event()

    def owner():
        with queue.account_mutex(engine, account_id) as acquired:
            assert acquired
            entered.set()
            assert attempted.wait(timeout=5)
            with factory() as db:
                return queue.claim(db, account_id)

    def competitor():
        assert entered.wait(timeout=5)
        try:
            with queue.account_mutex(engine, account_id) as acquired:
                assert not acquired
                return None
        finally:
            attempted.set()

    with ThreadPoolExecutor(max_workers=2) as pool:
        first, second = pool.submit(owner), pool.submit(competitor)
        assert first.result(timeout=10) is not None
        assert second.result(timeout=10) is None
