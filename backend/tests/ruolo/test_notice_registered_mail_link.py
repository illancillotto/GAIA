from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import Column, Table, Uuid, create_engine, event, func, select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import (
    RuoloTributiPayment,
    RuoloTributiPaymentImportJob,
    RuoloTributiRegisteredMail,
)
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.notice_register_schemas import OperatorChange
from app.modules.ruolo.services import notice_registered_mail_link as service
from app.modules.ruolo.services.notice_register import RegisterConflict, RegisterNotFound

from .test_notice_register import _avviso, _metadata


@pytest.fixture
def db():
    metadata = _metadata()
    metadata.remove(metadata.tables["ruolo_tributi_registered_mails"])
    Table("ruolo_tributi_posta_online_import_jobs", metadata, Column("id", Uuid, primary_key=True))
    for model in (RuoloTributiPaymentImportJob, RuoloTributiPayment, RuoloTributiRegisteredMail):
        model.__table__.to_metadata(metadata)
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata.create_all(engine)
    with Session(engine) as session:
        session.execute(metadata.tables["application_users"].insert().values(id=1))
        yield session
    engine.dispose()


def setup(db, count=2, tracking="619591492509"):
    subject_id = uuid4()
    subject_table = _metadata().tables["ana_subjects"]
    db.execute(subject_table.insert().values(id=subject_id))
    document = NoticeDocument(
        source_system="pdf_solleciti_2022_2023",
        source_key=str(uuid4()),
        document_number="12024222301234",
        tax_code="TESTCF",
        original_json={"immutable": "source"},
    )
    mail = RuoloTributiRegisteredMail(
        source_shipment_id=str(uuid4()),
        tracking_number=tracking,
        sent_at=datetime(2024, 11, 26, tzinfo=UTC),
        raw_payload_json={"raw": {"original": True}},
    )
    db.add_all([document, mail])
    db.flush()
    positions = []
    for year in range(2022, 2022 + count):
        role = _avviso(db, year)
        role.subject_id, role.codice_fiscale_raw = subject_id, "TESTCF"
        position = NoticePosition(
            document_id=document.id,
            source_namespace="incass",
            source_reference="0" + str(year) + "0000000001",
            tax_year=year,
            avviso_id=role.id,
        )
        db.add(position)
        db.flush()
        db.add(NoticeRecovery(position_id=position.id, state="da_verificare"))
        positions.append(position)
    db.add(NoticeNotification(document_id=document.id, state="da_verificare"))
    db.flush()
    return document, mail, positions


def change(document):
    return OperatorChange(
        actor_id=1, expected_version=document.version, reason="Incrocio verificato"
    )


@pytest.mark.parametrize("count", [1, 2])
@pytest.mark.parametrize("tracking", [None, "619591492509"])
def test_link_and_replay_preserve_scope(db, count, tracking):
    document, mail, positions = setup(db, count, tracking)
    evidence = NoticeEvidence(
        document_id=document.id,
        source_system="test",
        source_key=str(uuid4()),
        kind="ricevuta",
        reference="Verificata",
        original_json={},
    )
    db.add(evidence)
    db.flush()
    notification = db.get(NoticeNotification, document.id)
    notification.state, notification.notified_on, notification.evidence_id = (
        "perfezionata",
        date(2025, 1, 2),
        evidence.id,
    )
    db.flush()
    before = service._snapshot(notification)
    original = document.original_json.copy()
    selected = {position.avviso_id for position in positions}
    assert service.associate_registered_mail(db, document.id, mail.id, change(document)) is mail
    assert service.associated_avviso_ids(mail) == selected
    assert mail.subject_id is not None and mail.match_status == "matched"
    assert mail.raw_payload_json["raw"] == {"original": True}
    assert document.original_json == original
    assert service._snapshot(notification) == before
    assert db.scalar(select(func.count()).select_from(NoticePosition)) == count
    assert db.scalar(select(func.count()).select_from(NoticeAttempt)) == 1
    assert db.scalar(select(func.count()).select_from(NoticeDocument)) == 1
    version = document.version
    service.associate_registered_mail(db, document.id, mail.id, change(document))
    assert document.version == version
    assert db.scalar(select(func.count()).select_from(NoticeAudit)) == 1
    event_record = db.scalar(select(NoticeAudit))
    assert event_record.action == "associate_registered_mail"
    db.rollback()


@pytest.mark.parametrize("linked", [False, True])
def test_adopt_existing_attempt_and_audit(db, linked):
    document, mail, _ = setup(db)
    attempt = NoticeAttempt(
        document_id=document.id,
        source_system="manual",
        source_key=str(uuid4()),
        channel="posta",
        tracking_code=mail.tracking_number,
        registered_mail_id=mail.id if linked else None,
    )
    db.add(attempt)
    db.flush()
    service.associate_registered_mail(db, document.id, mail.id, change(document))
    assert attempt.registered_mail_id == mail.id
    assert db.scalar(select(func.count()).select_from(NoticeAttempt)) == 1


def test_repeated_send_same_document(db):
    document, mail, _ = setup(db)
    service.associate_registered_mail(db, document.id, mail.id, change(document))
    other = RuoloTributiRegisteredMail(
        source_shipment_id=str(uuid4()), tracking_number="619591492510"
    )
    db.add(other)
    db.flush()
    service.associate_registered_mail(db, document.id, other.id, change(document))
    assert service.associated_avviso_ids(other) == service.associated_avviso_ids(mail)
    assert db.scalar(select(func.count()).select_from(NoticeDocument)) == 1
    assert db.scalar(select(func.count()).select_from(NoticePosition)) == 2
    assert db.scalar(select(func.count()).select_from(NoticeAttempt)) == 2


@pytest.mark.parametrize(
    "problem",
    [
        "no_positions",
        "unlinked",
        "year",
        "cf",
        "blank_cf",
        "other_selection",
        "subject",
        "multiple",
        "attempt_document",
        "attempt_mail",
        "channel",
        "tracking",
    ],
)
def test_reject_inconsistent_scope_and_attempt(db, problem):
    document, mail, positions = setup(db)
    if problem == "no_positions":
        for position in positions:
            db.delete(db.get(NoticeRecovery, position.id))
        db.flush()
        for position in positions:
            db.delete(position)
    elif problem == "unlinked":
        positions[0].avviso_id = None
    elif problem == "year":
        positions[0].tax_year = 2021
    elif problem == "cf":
        document.tax_code = "OTHERCF"
    elif problem == "blank_cf":
        document.tax_code = " "
    elif problem == "other_selection":
        mail.raw_payload_json = {
            "manual_association": {"active": True, "avviso_ids": [str(uuid4())]}
        }
    elif problem == "subject":
        other_id = uuid4()
        db.execute(_metadata().tables["ana_subjects"].insert().values(id=other_id))
        mail.subject_id = other_id
    else:
        other_document, other_mail, _ = setup(db, tracking="other")
        db.add(
            NoticeAttempt(
                document_id=other_document.id if problem == "attempt_document" else document.id,
                source_system="test",
                source_key=str(uuid4()),
                channel="pec" if problem == "channel" else "raccomandata",
                tracking_code="other" if problem == "tracking" else mail.tracking_number,
                registered_mail_id=other_mail.id if problem == "attempt_mail" else mail.id,
            )
        )
        if problem == "multiple":
            db.add(
                NoticeAttempt(
                    document_id=document.id,
                    source_system="test",
                    source_key=str(uuid4()),
                    channel="raccomandata",
                    tracking_code=mail.tracking_number,
                )
            )
    db.flush()
    with pytest.raises(RegisterConflict):
        service.associate_registered_mail(db, document.id, mail.id, change(document))
    assert db.scalar(select(func.count()).select_from(NoticeAudit)) == 0


def test_missing_mail_and_stale_document(db):
    document, mail, _ = setup(db)
    with pytest.raises(RegisterNotFound):
        service.associate_registered_mail(db, document.id, uuid4(), change(document))
    stale = change(document).model_copy(update={"expected_version": document.version + 1})
    with pytest.raises(RegisterConflict):
        service.associate_registered_mail(db, document.id, mail.id, stale)


def test_postgresql_tracking_lock():
    database = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")), execute=Mock()
    )
    mail = SimpleNamespace(id=uuid4(), tracking_number="619591492509")
    service._lock_tracking(database, mail)
    assert database.execute.call_args.args[1] == {"identity": mail.tracking_number}
    mail.tracking_number = None
    service._lock_tracking(database, mail)
    assert database.execute.call_args.args[1] == {"identity": str(mail.id)}
