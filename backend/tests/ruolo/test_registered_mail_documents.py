from datetime import date
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.models.application_user import ApplicationUser
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiRegisteredMail
from app.modules.ruolo.registered_mail_document_models import RegisteredMailDocument
from app.modules.ruolo.registered_mail_document_schemas import CardUpload
from app.modules.ruolo.routes import registered_mail_document_routes as routes
from app.modules.ruolo.routes.registered_mail_routes import router as association_router
from app.modules.ruolo.services import registered_mail_documents as service
from app.modules.utenze.models import AnagraficaAuditLog, AnagraficaDocument, AnagraficaSubject
from app.modules.utenze.routes.documents import router as utenze_documents_router
from app.modules.utenze.routes.subjects import router as subjects_router
from app.services.nas_connector import NasConnectorError

from .test_notice_import import _metadata
from .test_notice_register import _avviso
from .test_notice_register_api import _headers, _seed_auth

PDF = b"%PDF-1.4\ncartolina test"
DAY = date(2025, 9, 12)


def metadata():
    result = _metadata()
    result.remove(result.tables["ana_subjects"])
    for model in (AnagraficaSubject, AnagraficaAuditLog):
        model.__table__.to_metadata(result)
    return result


@pytest.fixture
def setup(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )
    event.listen(
        engine, "connect", lambda connection, _: connection.execute("PRAGMA foreign_keys=ON")
    )
    metadata().create_all(engine)
    with engine.begin() as connection:
        _seed_auth(connection)
        connection.execute(
            update(ApplicationUser).where(ApplicationUser.id == 1).values(module_utenze=True)
        )
    with Session(engine) as db:
        subject = AnagraficaSubject(source_name_raw="MARTUCCI CARLA")
        db.add(subject)
        db.flush()
        notice = _avviso(db, 2023)
        notice.subject_id = subject.id
        db.flush()
        mail = RuoloTributiRegisteredMail(
            subject_id=subject.id,
            avviso_id=notice.id,
            match_status="matched",
            source_shipment_id="shipment",
            tracking_number="619592000378",
        )
        db.add(mail)
        db.commit()
        mail_id, subject_id, notice_id = mail.id, subject.id, notice.id

    def storage(subject_id, filename, content):
        path = tmp_path / f"{uuid4()}-{filename}"
        path.write_bytes(content)
        return str(path)

    monkeypatch.setattr(service, "store_uploaded_document", storage)
    app = FastAPI()
    app.include_router(routes.router, prefix="/ruolo")
    app.include_router(association_router, prefix="/ruolo")
    app.include_router(subjects_router, prefix="/utenze")
    app.include_router(utenze_documents_router, prefix="/utenze")

    def database():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = database
    with TestClient(app) as client:
        client.headers.update(_headers(1))
        yield SimpleNamespace(
            client=client,
            engine=engine,
            mail_id=mail_id,
            subject_id=subject_id,
            notice_id=notice_id,
            tmp_path=tmp_path,
        )
    engine.dispose()


def post(setup, **kwargs):
    data = {
        "tracking_number": "61959200037-8",
        "scanned_on": str(DAY),
        "source_reference": "NAS/Cartoline.xlsx:riga1012",
    }
    data.update(kwargs.pop("data", {}))
    return setup.client.post(
        f"/ruolo/tributi/raccomandate/{setup.mail_id}/cartoline",
        data=data,
        files={"file": kwargs.pop("file", ("cartolina.pdf", PDF, "application/pdf"))},
        **kwargs,
    )


def test_upload_shared_document_idempotence_and_download(setup):
    initial = post(setup)
    assert initial.status_code == 200, initial.text
    card = initial.json()
    assert card["scanned_on"] == "2025-09-12"
    assert card["tracking_number"] == "619592000378"
    assert post(setup).json()["id"] == card["id"]
    base = f"/ruolo/tributi/raccomandate/{setup.mail_id}/cartoline"
    assert setup.client.get(base).json() == [card]
    assert setup.client.get(base + f"/{card['id']}/download").content == PDF
    assert setup.client.get(base + f"/{uuid4()}/download").status_code == 404
    docs = setup.client.get(f"/utenze/subjects/{setup.subject_id}/documents")
    assert docs.status_code == 200, docs.text
    assert docs.json()[0]["id"] == card["document_id"]
    assert docs.json()[0]["doc_type"] == "cartolina_raccomandata"
    assert setup.client.get(f"/utenze/documents/{card['document_id']}/download").content == PDF
    with Session(setup.engine) as db:
        assert db.scalar(select(func.count()).select_from(AnagraficaDocument)) == 1
        assert db.scalar(select(func.count()).select_from(AnagraficaAuditLog)) == 1
        mail = db.get(RuoloTributiRegisteredMail, setup.mail_id)
        assert mail.sent_at is None and mail.status_label is None and mail.annualita_json is None
        link = db.get(RegisteredMailDocument, UUID(card["id"]))
        assert link.created_by == 1
    assert len(list(setup.tmp_path.iterdir())) == 1


def test_multiple_cards_no_overwrite_or_duplicate(setup):
    first = post(setup).json()
    second = post(setup, file=("other.pdf", PDF + b"\nother", "application/pdf")).json()
    assert first["document_id"] != second["document_id"]
    cards = setup.client.get(f"/ruolo/tributi/raccomandate/{setup.mail_id}/cartoline").json()
    assert len(cards) == 2
    assert post(setup).json()["id"] == first["id"]


def test_linked_card_delete_and_reset_fail_with_conflict(setup, monkeypatch):
    from app.modules.utenze.routes import documents

    monkeypatch.setattr(documents.settings, "utenze_delete_password", "")
    monkeypatch.setattr(documents.settings, "anagrafica_delete_password", "")
    card = post(setup).json()
    assert setup.client.delete(f"/utenze/documents/{card['document_id']}").status_code == 409
    assert setup.client.post("/utenze/reset", json={"confirm": "RESET UTENZE"}).status_code == 409
    assert setup.client.get(f"/utenze/documents/{card['document_id']}/download").content == PDF


def test_unlinked_document_can_be_deleted_while_card_is_retained(setup, monkeypatch):
    from app.modules.utenze.routes import documents

    monkeypatch.setattr(documents.settings, "utenze_delete_password", "")
    monkeypatch.setattr(documents.settings, "anagrafica_delete_password", "")
    card = post(setup).json()
    with Session(setup.engine) as db:
        ordinary_document = AnagraficaDocument(
            subject_id=setup.subject_id,
            filename="documento.pdf",
            doc_type="other",
        )
        db.add(ordinary_document)
        db.commit()
        document_id = ordinary_document.id
    assert setup.client.delete(f"/utenze/documents/{document_id}").status_code == 204
    with Session(setup.engine) as db:
        assert db.get(AnagraficaDocument, document_id) is None
        assert db.get(AnagraficaDocument, UUID(card["document_id"])) is not None
    assert setup.client.get(f"/utenze/documents/{card['document_id']}/download").content == PDF


@pytest.mark.parametrize(
    "data,status",
    [
        ({"tracking_number": "123"}, 422),
        ({"tracking_number": "x"}, 422),
        ({"tracking_number": "619592000379"}, 409),
        ({"scanned_on": "invalid"}, 422),
    ],
)
def test_invalid_metadata_no_files(setup, data, status):
    assert post(setup, data=data).status_code == status
    assert not list(setup.tmp_path.iterdir())


@pytest.mark.parametrize(
    "filename,content,status",
    [
        ("card.txt", PDF, 422),
        ("card.pdf", b"not pdf", 422),
        ("x" * 256 + ".pdf", PDF, 422),
        ("card.pdf", b"%PDF-" + b"x" * service.MAX_PDF_BYTES, 413),
    ],
)
def test_invalid_files(setup, filename, content, status):
    assert post(setup, file=(filename, content, "application/pdf")).status_code == status
    assert not list(setup.tmp_path.iterdir())


@pytest.mark.parametrize(
    "changes",
    [
        {"subject_id": None},
        {"avviso_id": None},
        {"match_status": "ambiguous"},
        {"anomaly_key": "review"},
        {"recipient_name": "A Riordino fondiario"},
    ],
)
def test_unconfirmed_identity_blocked(setup, changes):
    with setup.engine.begin() as connection:
        connection.execute(
            update(RuoloTributiRegisteredMail)
            .where(RuoloTributiRegisteredMail.id == setup.mail_id)
            .values(**changes)
        )
    assert post(setup).status_code == 409
    assert not list(setup.tmp_path.iterdir())


def test_unknown_mail_and_inconsistent_notice(setup):
    assert setup.client.get(f"/ruolo/tributi/raccomandate/{uuid4()}/cartoline").status_code == 404
    with Session(setup.engine) as db:
        mail = db.get(RuoloTributiRegisteredMail, setup.mail_id)
        mail.raw_payload_json = {
            "manual_association": {"active": True, "avviso_ids": [str(uuid4())]}
        }
        db.commit()
    assert post(setup).status_code == 409


@pytest.mark.parametrize("user_id", [2, 3, 4, 5])
def test_upload_permissions(setup, user_id):
    assert post(setup, headers=_headers(user_id)).status_code == (401 if user_id == 4 else 403)


def test_readonly_reader_and_unauthenticated(setup):
    card = post(setup).json()
    base = f"/ruolo/tributi/raccomandate/{setup.mail_id}/cartoline"
    assert setup.client.get(base, headers=_headers(2)).status_code == 200
    assert setup.client.get(base + f"/{card['id']}/download", headers=_headers(2)).content == PDF
    setup.client.headers.clear()
    assert setup.client.get(base).status_code == 401


def test_subject_change_and_mismatched_download_blocked(setup):
    card = post(setup).json()
    with Session(setup.engine) as db:
        service.validate_subject_change(db, setup.mail_id, [db.get(RuoloAvviso, setup.notice_id)])
        with pytest.raises(HTTPException) as failure:
            service.validate_subject_change(db, setup.mail_id, [])
        assert failure.value.status_code == 409
    changed = setup.client.patch(
        f"/ruolo/tributi/raccomandate/{setup.mail_id}/association", json={"avviso_ids": []}
    )
    assert changed.status_code == 409
    with setup.engine.begin() as connection:
        connection.execute(
            update(RuoloTributiRegisteredMail)
            .where(RuoloTributiRegisteredMail.id == setup.mail_id)
            .values(subject_id=None)
        )
    assert (
        setup.client.get(
            f"/ruolo/tributi/raccomandate/{setup.mail_id}/cartoline/{card['id']}/download"
        ).status_code
        == 409
    )


def test_storage_nas_success_and_failure(setup, monkeypatch):
    connector = Mock()
    monkeypatch.setattr(service, "get_nas_client", lambda: connector)
    monkeypatch.setattr(service, "_store_document_on_nas", lambda *args: "nas/card.pdf")
    subject = SimpleNamespace(id=setup.subject_id, nas_folder_path="nas/subject")
    local, nas = service.store_pdf(subject, "card.pdf", PDF)
    assert Path(local).read_bytes() == PDF and nas == "nas/card.pdf"
    connector.close.assert_called_once()

    def failing(*args):
        raise NasConnectorError("offline")

    monkeypatch.setattr(service, "_store_document_on_nas", failing)
    with Session(setup.engine) as db:
        db.get(AnagraficaSubject, setup.subject_id).nas_folder_path = "nas/subject"
        db.commit()
    assert post(setup).status_code == 502
    assert len(list(setup.tmp_path.iterdir())) == 1


def test_database_failure_rolls_back_and_cleans_local(setup, monkeypatch):
    with Session(setup.engine) as db:
        monkeypatch.setattr(db, "commit", Mock(side_effect=RuntimeError("commit failed")))
        with pytest.raises(RuntimeError):
            service.upload(
                db,
                mail_id=setup.mail_id,
                payload=CardUpload("card.pdf", PDF, "619592000378", DAY, None),
                actor_id=1,
            )
        assert db.scalar(select(func.count()).select_from(RegisteredMailDocument)) == 0
    assert not list(setup.tmp_path.iterdir())


def test_missing_subject_fail_closed():
    db = Mock()
    mail = SimpleNamespace(
        recipient_name="A",
        shipment_name=None,
        subject_id=uuid4(),
        avviso_id=uuid4(),
        match_status="matched",
        anomaly_key=None,
        raw_payload_json=None,
    )
    db.get.side_effect = [SimpleNamespace(subject_id=mail.subject_id), None]
    with pytest.raises(HTTPException) as failure:
        service.confirmed_subject(db, mail)
    assert failure.value.status_code == 409


def test_migration_and_restrict_deletion(setup):
    migration = load_python_file(
        str(Path(__file__).parents[2] / "alembic/versions"),
        "20261002_1030_registered_mail_documents.py",
    )
    with setup.engine.begin() as connection:
        migration.op = Operations(MigrationContext.configure(connection))
        migration.downgrade()
        migration.upgrade()
    card = post(setup).json()
    with Session(setup.engine) as db:
        with pytest.raises(IntegrityError):
            db.delete(db.get(AnagraficaDocument, UUID(card["document_id"])))
            db.commit()
        db.rollback()
