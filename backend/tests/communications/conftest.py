"""Synthetic accounts, multipage PDFs and accounting boundary; no network access."""

import io
from datetime import date
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pypdf import PdfWriter
from ruolo.poste_dispatch_fixtures import dispatch_metadata, seed_batch_item
from ruolo.test_notice_register import _avviso
from ruolo.test_notice_register_api import _headers, _seed_auth
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.modules.communications import admin, models, registry, ruolo_source
from app.modules.communications.router import router
from app.modules.communications.schemas import AccountInput
from app.modules.ruolo.models import RuoloAvviso, RuoloTributiNoticeNumber
from app.modules.ruolo.notice_register_models import (
    NoticeDocument,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.utenze.models import AnagraficaCompany, AnagraficaPerson, AnagraficaSubject


def pdf(count=3):
    output = io.BytesIO()
    writer = PdfWriter()
    for _ in range(count):
        writer.add_blank_page(width=595, height=842)
    writer.write(output)
    return output.getvalue()


def metadata():
    value = dispatch_metadata()
    value.remove(value.tables["ana_subjects"])
    for model in (AnagraficaSubject, AnagraficaPerson, AnagraficaCompany):
        model.__table__.to_metadata(value)
    for table in Base.metadata.tables.values():
        if table.name.startswith("communication_"):
            table.to_metadata(value)
    return value


def account_input(channel="pec", **overrides):
    return AccountInput(
        **{
            "name": f"Synthetic {channel}",
            "channel": channel,
            "provider": "synthetic",
            "sender": f"sender-{channel}@example.org",
            "smtp_host": "smtp.example.org",
            "smtp_port": 465,
            "imap_host": "imap.example.org",
            "imap_port": 993,
            "username": "synthetic",
            "secret_ref": "synthetic",
            "active": True,
            "paused": False,
            "is_default": True,
        }
        | overrides
    )


@pytest.fixture
def api(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def fk(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata().create_all(engine)
    factory = sessionmaker(engine, autoflush=False, expire_on_commit=False)
    with engine.begin() as connection:
        _seed_auth(connection)
    with factory() as db:
        source = seed_batch_item(db, tmp_path, content=pdf())
        number = RuoloTributiNoticeNumber(
            emission_year=2026,
            progressive=1,
            notice_number=source.payload_json["notice_number"],
            identity_key="a" * 64,
            status="generated",
        )
        db.add(number)
        avviso = _avviso(db, year=2021)
        avviso.codice_fiscale_raw = source.codice_fiscale
        source.avviso_ids_json = [str(avviso.id)]
        for system, key in (("incass", "historical-1"), ("gaia_batch_item", str(source.id))):
            document = NoticeDocument(
                source_system=system,
                source_key=key,
                document_number=number.notice_number,
                tax_code=source.codice_fiscale,
                original_json={},
            )
            db.add(document)
            db.flush()
            position = NoticePosition(
                document_id=document.id,
                source_namespace="gaia",
                source_reference=str(avviso.id),
                tax_year=2021,
                avviso_id=avviso.id,
            )
            db.add(position)
            db.flush()
            db.add(NoticeNotification(document_id=document.id, state="nessuna_evidenza"))
            db.add(
                NoticeRecovery(
                    position_id=position.id,
                    state="non_affidato_verificato",
                    verified_on=date.today(),
                    evidence_reference="synthetic review",
                )
            )
        accounts = [
            registry.save_account(db, account_input(channel), 1) for channel in ("pec", "email")
        ]
        db.add(models.CommunicationControl(id=1, paused=False))
        db.commit()
        source_id, account_ids = source.id, [account.id for account in accounts]
    summary = {
        "saldo_amount": "10.00",
        "due_amount": "10.00",
        "paid_amount": "0.00",
        "payment_status": "unpaid",
        "calculation_policy": "internal_gaia",
        "workflow_status": "da_lavorare",
        "reminder_enabled": True,
        "mailing_delivery": None,
    }

    def accounting(db, identity):
        record = db.get(RuoloAvviso, identity)
        return {"avviso": record, **summary} if record else None

    monkeypatch.setattr(ruolo_source.repo, "get_tributi_avviso", accounting)
    # Unexpected socket creation fails every test. Adapter contracts inject fake clients.
    monkeypatch.setattr(
        "socket.create_connection", lambda *a, **k: pytest.fail("Real network forbidden")
    )
    app = FastAPI()
    app.include_router(router)
    app.include_router(admin.router)

    def database():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = database
    with TestClient(app) as client:
        client.headers.update(_headers())
        yield SimpleNamespace(
            client=client,
            session=factory,
            engine=engine,
            source_id=source_id,
            account_ids=account_ids,
            summary=summary,
            tmp_path=tmp_path,
        )
    engine.dispose()


def create(api, channel="pec", **overrides):
    response = api.client.post(
        "/communications/messages",
        json={
            "source_entity_id": str(api.source_id),
            "channel": channel,
            "recipient": "recipient@example.org",
            "subject": "Sollecito sintetico",
            "body": "Contenuto di prova",
            **overrides,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def approved(api, channel="pec"):
    value = create(api, channel)
    base = f"/communications/messages/{value['id']}"
    part = value["attachments"][0]
    preview = api.client.get(f"{base}/attachments/{part['id']}/preview")
    assert preview.status_code == 200
    assert (
        api.client.post(
            f"{base}/attachments/{part['id']}/rendered",
            json={
                "review_id": preview.headers["X-Communication-Review"],
                "expected_version": 1,
                "pages": part["pages"],
                "sha256": part["sha256"],
            },
        ).status_code
        == 200
    )
    assert api.client.post(f"{base}/validate", json={"expected_version": 1}).status_code == 200
    from app.modules.communications.schemas import CHECKS

    response = api.client.post(
        f"{base}/approve",
        json={"expected_version": 1, "confirmed": True, "checklist": dict.fromkeys(CHECKS, True)},
    )
    assert response.status_code == 200, response.text
    return response.json()
