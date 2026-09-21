from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from pydantic import ValidationError
from sqlalchemy import Column, Integer, MetaData, Table, Uuid, create_engine, event, inspect, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.db.base import Base
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob
from app.modules.ruolo.notice_import_models import NoticeImportBatch, NoticeImportRow
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.notice_register_schemas import (
    DocumentDetails,
    EvidenceInput,
    HistoricalDocument,
    NotificationDecision,
    OperatorChange,
    RecoveryDecision,
)
from app.modules.ruolo.services import notice_register as service

REGISTER_MODELS = (
    NoticeDocument,
    NoticePosition,
    NoticeAttempt,
    NoticeEvidence,
    NoticeNotification,
    NoticeRecovery,
    NoticeAudit,
)


def _metadata():
    metadata = MetaData()
    Table("application_users", metadata, Column("id", Integer, primary_key=True))
    Table("ana_subjects", metadata, Column("id", Uuid, primary_key=True))
    Table("ruolo_tributi_registered_mails", metadata, Column("id", Uuid, primary_key=True))
    for model in (RuoloImportJob, RuoloAvviso, *REGISTER_MODELS):
        model.__table__.to_metadata(metadata)
    return metadata


@pytest.fixture(scope="module", params=["sqlite", "postgresql"])
def register_engine(request):
    if request.param == "sqlite":
        engine = create_engine("sqlite://")

        @event.listens_for(engine, "connect")
        def enable_foreign_keys(connection, _):
            connection.execute("PRAGMA foreign_keys=ON")

        _metadata().create_all(engine)
        yield engine
        engine.dispose()
        return
    url = os.getenv("GAIA_TEST_POSTGRES_URL")
    if not url:
        pytest.skip("GAIA_TEST_POSTGRES_URL non configurato")
    schema = f"test_operational_notice_{uuid.uuid4().hex}"
    admin = create_engine(url)
    assert admin.dialect.name == "postgresql"
    with admin.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        _metadata().create_all(engine)
        yield engine
    finally:
        engine.dispose()
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        admin.dispose()


@pytest.fixture
def db(register_engine):
    with register_engine.connect() as connection:
        transaction = connection.begin()
        with Session(connection, autoflush=False) as session:
            connection.execute(_metadata().tables["application_users"].insert().values(id=1))
            yield session
        if transaction.is_active:
            transaction.rollback()


def _change(version=1):
    return OperatorChange(
        actor_id=1, reason="Verifica documentale operatore", expected_version=version
    )


def _historical(**overrides):
    values = {
        "document_number": "12024222303799",
        "tax_code": "TESTCF",
        "issued_on": "2024-06-01",
        "positions": [
            {"source_namespace": "incass", "source_reference": "020220001834880", "tax_year": 2022},
            {"source_namespace": "incass", "source_reference": "020230011722820", "tax_year": 2023},
        ],
    }
    return HistoricalDocument(**(values | overrides))


def _document(db, **overrides):
    return service.create_historical_document(db, _historical(**overrides), _change())


def _positions(db, document):
    return list(
        db.scalars(
            select(NoticePosition)
            .where(
                NoticePosition.document_id == document.id,
            )
            .order_by(NoticePosition.tax_year)
        )
    )


def _avviso(db, year=2022):
    job = RuoloImportJob(anno_tributario=year)
    db.add(job)
    db.flush()
    avviso = RuoloAvviso(import_job_id=job.id, anno_tributario=year, codice_cnc=str(uuid.uuid4()))
    db.add(avviso)
    db.flush()
    return avviso


def _evidence(db, document, **overrides):
    values = {
        "source_system": "manual",
        "source_key": str(uuid.uuid4()),
        "kind": "ricevuta",
        "reference": "Archivio, ricevuta 123",
        "original_json": {"raw_date": "29/06/204"},
        "occurred_on": date(2024, 6, 29),
    }
    return service.record_evidence(
        db,
        document.id,
        EvidenceInput(**(values | overrides)),
        _change(document.version),
    )


def _attempt(db, document):
    attempt = NoticeAttempt(
        document_id=document.id,
        source_system="poste",
        source_key=str(uuid.uuid4()),
        channel="posta",
    )
    db.add(attempt)
    db.flush()
    return attempt


def test_models_registered_in_application_metadata():
    assert all(model.__tablename__ in Base.metadata.tables for model in REGISTER_MODELS)


def test_historical_creation_keeps_annual_namespaces_and_no_debt(db):
    document = _document(db)
    positions = _positions(db, document)
    assert len(positions) == 2
    assert positions[0].source_reference == "020220001834880"
    assert positions[1].tax_year == 2023
    assert all(position.avviso_id is None for position in positions)
    assert db.get(NoticeNotification, document.id).state == "da_verificare"
    assert all(db.get(NoticeRecovery, p.id).state == "da_verificare" for p in positions)
    assert list(db.scalars(select(RuoloAvviso))) == []
    audit = db.scalar(select(NoticeAudit).where(NoticeAudit.document_id == document.id))
    assert audit.actor_id == 1 and audit.version == 1
    assert (
        audit.after_json["document"]["original_json"]["document_number"] == document.document_number
    )


def test_empty_historical_document_is_retained_for_anomalies(db):
    document = _document(db, positions=[])
    assert _positions(db, document) == []
    assert document.source_system == "manual"


def test_revision_preserves_original_and_audits_versions(db):
    document = _document(db)
    original = document.original_json.copy()
    updated = service.revise_document(
        db,
        document.id,
        DocumentDetails(document_number="corretto"),
        _change(),
    )
    assert updated.version == 2
    assert updated.original_json == original
    audit = db.scalar(
        select(NoticeAudit).where(
            NoticeAudit.document_id == document.id,
            NoticeAudit.version == 2,
        )
    )
    assert audit.before_json["document_number"] == original["document_number"]
    assert audit.after_json["document_number"] == "corretto"
    assert audit.before_json["version"] == 1
    assert audit.after_json["version"] == 2


def test_missing_and_stale_documents_are_rejected(db):
    with pytest.raises(ValueError, match="non trovato"):
        service.revise_document(db, uuid.uuid4(), DocumentDetails(document_number="x"), _change())
    document = _document(db)
    with pytest.raises(service.RegisterConflict, match="ricaricare"):
        service.revise_document(db, document.id, DocumentDetails(document_number="x"), _change(2))
    with pytest.raises(service.RegisterConflict, match="versione 1"):
        service.create_historical_document(db, _historical(), _change(2))
    assert document.version == 1


def test_link_unlink_and_relink_invalidate_previous_scope_decisions(db):
    document = _document(db)
    position = _positions(db, document)[0]
    avviso = _avviso(db)
    service.link_position(db, document.id, position.id, avviso.id, _change())
    evidence = _evidence(db, document)
    service.assess_notification(
        db,
        document.id,
        NotificationDecision(
            state="perfezionata",
            notified_on=date(2024, 6, 29),
            evidence_id=evidence.id,
        ),
        _change(document.version),
    )
    service.assess_recovery(
        db,
        document.id,
        position.id,
        RecoveryDecision(
            state="affidato",
            case_reference="STEP-1",
            verified_on=date.today(),
            evidence_reference="Protocollo 42",
            amount=Decimal("100.25"),
        ),
        _change(document.version),
    )
    previous_version = document.version
    service.link_position(db, document.id, position.id, avviso.id, _change(previous_version))
    assert document.version == previous_version
    service.link_position(db, document.id, position.id, None, _change(previous_version))
    assert position.avviso_id is None
    assert db.get(NoticeNotification, document.id).state == "da_verificare"
    assert db.get(NoticeRecovery, position.id).state == "da_verificare"
    audit = db.scalar(
        select(NoticeAudit).where(
            NoticeAudit.document_id == document.id,
            NoticeAudit.version == document.version,
        )
    )
    assert audit.before_json["notification"]["state"] == "perfezionata"
    assert audit.before_json["recovery"]["case_reference"] == "STEP-1"
    assert audit.before_json["recovery"]["amount"] == "100.25"
    assert db.get(NoticeEvidence, evidence.id).original_json["raw_date"] == "29/06/204"
    service.link_position(db, document.id, position.id, avviso.id, _change(document.version))
    assert position.avviso_id == avviso.id


def test_cumulative_document_links_multiple_avvisi(db):
    document = _document(db)
    for position in _positions(db, document):
        avviso = _avviso(db, position.tax_year)
        service.link_position(db, document.id, position.id, avviso.id, _change(document.version))
    assert len({p.avviso_id for p in _positions(db, document)}) == 2


def test_link_validates_ownership_year_and_duplicate_avviso(db):
    document = _document(db)
    position = _positions(db, document)[0]
    other = _document(db)
    other_position = _positions(db, other)[0]
    for position_id in (uuid.uuid4(), other_position.id):
        with pytest.raises(ValueError, match="non appartenente"):
            service.link_position(db, document.id, position_id, None, _change())
    for avviso_id in (uuid.uuid4(), _avviso(db, 2023).id):
        with pytest.raises(ValueError, match="annualita"):
            service.link_position(db, document.id, position.id, avviso_id, _change())
    avviso = _avviso(db)
    service.link_position(db, document.id, position.id, avviso.id, _change())
    extra = NoticePosition(
        document_id=document.id, source_namespace="other", source_reference="extra", tax_year=2022
    )
    db.add(extra)
    db.flush()
    with pytest.raises(ValueError, match="gia collegato"):
        service.link_position(db, document.id, extra.id, avviso.id, _change(document.version))


def test_evidence_and_poste_outcome_do_not_automatically_prove_notification_or_step(db):
    document = _document(db)
    attempt = _attempt(db, document)
    evidence = _evidence(db, document, attempt_id=attempt.id, kind="Servizio erogato")
    assert evidence.attempt_id == attempt.id
    assert db.get(NoticeNotification, document.id).state == "da_verificare"
    assert db.get(NoticeRecovery, _positions(db, document)[0].id).state == "da_verificare"
    for attempt_id in (uuid.uuid4(), _attempt(db, _document(db)).id):
        with pytest.raises(ValueError, match="Tentativo"):
            _evidence(db, document, attempt_id=attempt_id)


def test_notification_decision_requires_own_evidence_and_stays_local(db):
    document = _document(db)
    other = _document(db)
    other_evidence = _evidence(db, other)
    for evidence_id in (uuid.uuid4(), other_evidence.id):
        with pytest.raises(ValueError, match="Evidenza"):
            service.assess_notification(
                db,
                document.id,
                NotificationDecision(
                    state="perfezionata",
                    notified_on=date(2024, 6, 29),
                    evidence_id=evidence_id,
                ),
                _change(),
            )
    own_evidence = _evidence(db, document)
    decision = service.assess_notification(
        db,
        document.id,
        NotificationDecision(
            state="perfezionata",
            notified_on=date(2024, 6, 29),
            evidence_id=own_evidence.id,
        ),
        _change(document.version),
    )
    assert decision.state == "perfezionata"
    assert db.get(NoticeNotification, other.id).state == "da_verificare"
    assert all(
        db.get(NoticeRecovery, p.id).state == "da_verificare" for p in _positions(db, document)
    )
    service.assess_notification(
        db,
        document.id,
        NotificationDecision(
            state="tentativo_senza_notifica",
        ),
        _change(document.version),
    )
    assert decision.notified_on is None


def test_step_is_independent_and_position_scoped(db):
    document = _document(db)
    first, second = _positions(db, document)
    service.assess_recovery(
        db,
        document.id,
        first.id,
        RecoveryDecision(
            state="non_affidato_verificato",
            verified_on=date.today(),
            evidence_reference="Report STEP",
        ),
        _change(),
    )
    assert db.get(NoticeRecovery, first.id).state == "non_affidato_verificato"
    assert db.get(NoticeRecovery, second.id).state == "da_verificare"
    assert db.get(NoticeNotification, document.id).state == "da_verificare"
    service.assess_recovery(
        db,
        document.id,
        first.id,
        RecoveryDecision(
            state="da_verificare",
        ),
        _change(document.version),
    )
    assert db.get(NoticeRecovery, first.id).evidence_reference is None


@pytest.mark.parametrize(
    "payload",
    [
        {"state": "perfezionata"},
        {"state": "perfezionata", "notified_on": date.today()},
        {
            "state": "perfezionata",
            "notified_on": date.today() + timedelta(days=1),
            "evidence_id": uuid.uuid4(),
        },
        {"state": "da_verificare", "notified_on": date.today()},
        {"state": "notificato"},
    ],
)
def test_invalid_notification_decisions(payload):
    with pytest.raises(ValidationError):
        NotificationDecision(**payload)


@pytest.mark.parametrize(
    "payload",
    [
        {"state": "non_affidato_verificato"},
        {"state": "non_affidato_verificato", "verified_on": date.today()},
        {
            "state": "non_affidato_verificato",
            "verified_on": date.today() + timedelta(days=1),
            "evidence_reference": "report",
        },
        {"state": "affidato", "verified_on": date.today(), "evidence_reference": "report"},
        {"state": "chiuso", "verified_on": date.today(), "evidence_reference": "report"},
        {"state": "da_verificare", "amount": "-0.01"},
        {"state": "da_verificare", "amount": "1.001"},
        {"state": "da_verificare", "amount": "NaN"},
    ],
)
def test_invalid_step_decisions(payload):
    with pytest.raises(ValidationError):
        RecoveryDecision(**payload)


def test_input_validation_preserves_reference_strings():
    original = _historical()
    assert original.positions[0].source_reference.startswith("0")
    with pytest.raises(ValidationError, match="duplicati"):
        _historical(positions=[original.positions[0], original.positions[0]])
    with pytest.raises(ValidationError):
        _change().model_validate({"actor_id": 1, "reason": "   ", "expected_version": 1})
    with pytest.raises(ValidationError):
        _historical(document_number=" ")
    with pytest.raises(ValidationError):
        _historical(source_system="gaia")


def test_migration_roundtrip_and_model_parity(db):
    connection = db.connection()
    metadata = _metadata()
    tables = [metadata.tables[model.__tablename__] for model in REGISTER_MODELS]
    metadata.drop_all(connection, tables=tables)
    path = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    revision = load_python_file(str(path), "20260917_0900_ruolo_notice_register.py")
    imports = load_python_file(str(path), "20260918_0900_ruolo_notice_import.py")
    reconciliation = load_python_file(str(path), "20260918_1500_notice_reconciliation.py")
    for model in (NoticeImportBatch, NoticeImportRow):
        model.__table__.to_metadata(metadata)
    assert revision.down_revision == "20260915_1400"
    with Operations.context(MigrationContext.configure(connection)):
        revision.upgrade()
        imports.upgrade()
        reconciliation.upgrade()
        assert compare_metadata(MigrationContext.configure(connection), metadata) == []
        reconciliation.downgrade()
        imports.downgrade()
        revision.downgrade()
        assert not inspect(connection).has_table("ruolo_notice_documents")
        revision.upgrade()
        imports.upgrade()
        reconciliation.upgrade()
        assert compare_metadata(MigrationContext.configure(connection), metadata) == []
    assert _document(db).version == 1


def test_database_rejects_cross_document_evidence(db):
    document = _document(db)
    other = _document(db)
    other_evidence = _evidence(db, other)
    notification = db.get(NoticeNotification, document.id)
    with pytest.raises(IntegrityError), db.begin_nested():
        notification.state = "perfezionata"
        notification.notified_on = date.today()
        notification.evidence_id = other_evidence.id
        db.flush()


@pytest.mark.parametrize("state", ["perfezionata", "unknown"])
def test_database_rejects_unproven_or_invalid_notification(db, state):
    document = _document(db)
    notification = db.get(NoticeNotification, document.id)
    with pytest.raises(IntegrityError), db.begin_nested():
        notification.state = state
        db.flush()


def test_database_rejects_unproven_recovery_and_source_duplicates(db):
    document = _document(db)
    recovery = db.get(NoticeRecovery, _positions(db, document)[0].id)
    with pytest.raises(IntegrityError), db.begin_nested():
        recovery.state = "affidato"
        db.flush()
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(
            NoticeDocument(
                source_system=document.source_system,
                source_key=document.source_key,
                document_number="duplicate",
                original_json={},
            )
        )
        db.flush()


def test_transaction_rollback_includes_document_and_audit(db):
    with db.begin_nested() as transaction:
        document = _document(db)
        document_id = document.id
        transaction.rollback()
    assert db.get(NoticeDocument, document_id) is None
    assert db.scalar(select(NoticeAudit.id).where(NoticeAudit.document_id == document_id)) is None


def test_concurrent_operators_cannot_overwrite_each_other(register_engine):
    if register_engine.dialect.name != "postgresql":
        pytest.skip("Concorrenza e row lock richiedono PostgreSQL")
    with Session(register_engine) as seed:
        seed.execute(_metadata().tables["application_users"].insert().values(id=1))
        document_id = _document(seed).id
        seed.commit()

    def edit(number):
        with Session(register_engine) as session:
            try:
                service.revise_document(
                    session,
                    document_id,
                    DocumentDetails(
                        document_number=number,
                    ),
                    _change(),
                )
                session.commit()
                return "updated"
            except service.RegisterConflict:
                session.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(edit, ["operator-1", "operator-2"])) == ["conflict", "updated"]
    with Session(register_engine) as session:
        assert session.get(NoticeDocument, document_id).version == 2
        assert (
            len(
                list(
                    session.scalars(
                        select(NoticeAudit).where(
                            NoticeAudit.document_id == document_id,
                        )
                    )
                )
            )
            == 2
        )
