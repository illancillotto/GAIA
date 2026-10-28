"""Shared SQLite schema and seed data for the Posta Online outbox tests."""

from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.models.posta_online import PostaOnlineCredential, PostaOnlineRegisteredMailSyncJob
from app.models.section_permission import RoleSectionPermission, Section, UserSectionPermission
from app.modules.ruolo.models import (
    RuoloTributiNoticeNumber,
    RuoloTributiPayment,
    RuoloTributiPaymentImportJob,
    RuoloTributiPostaOnlineImportJob,
    RuoloTributiRegisteredMail,
    RuoloTributiReminderBatch,
    RuoloTributiReminderBatchItem,
)
from app.modules.ruolo.poste_dispatch_models import (
    PosteDispatchEvent,
    PosteDispatchItem,
    PosteDispatchLot,
)

from .test_notice_register import _metadata

PDF = b"%PDF-1.4 prova GAIA\n%%EOF"
MODELS = (
    ApplicationUser,
    Section,
    RoleSectionPermission,
    UserSectionPermission,
    RuoloTributiPostaOnlineImportJob,
    RuoloTributiPaymentImportJob,
    RuoloTributiPayment,
    RuoloTributiRegisteredMail,
    RuoloTributiReminderBatch,
    RuoloTributiNoticeNumber,
    RuoloTributiReminderBatchItem,
    PostaOnlineCredential,
    PostaOnlineRegisteredMailSyncJob,
    PosteDispatchLot,
    PosteDispatchItem,
    PosteDispatchEvent,
)


def dispatch_metadata():
    metadata = _metadata()
    for name in ("application_users", "ruolo_tributi_registered_mails"):
        metadata.remove(metadata.tables[name])
    for model in MODELS:
        model.__table__.to_metadata(metadata)
    return metadata


def dispatch_engine(**kwargs):
    engine = create_engine("sqlite://", **kwargs)

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    dispatch_metadata().create_all(engine)
    return engine


def seed_user(db: Session, user_id: int = 1) -> None:
    db.add(
        ApplicationUser(
            id=user_id,
            username=f"poste-{user_id}",
            email=f"poste-{user_id}@example.test",
            password_hash="unused",
            role="admin",
            module_ruolo=True,
            is_active=True,
        )
    )
    db.flush()


def payload(notice_number: str = "020217801062586", **overrides) -> dict:
    return {
        "notice_number": notice_number,
        "display_name": "Rossi Mario",
        "comune": "ORISTANO",
        "avvisi": [{"residenza_raw": "VIA CAGLIARI 170 09170 ORISTANO (OR)"}],
    } | overrides


def seed_batch_item(db: Session, tmp_path: Path, **overrides) -> RuoloTributiReminderBatchItem:
    batch = RuoloTributiReminderBatch(
        title=overrides.pop("title", "Solleciti 2021"), status="generated"
    )
    db.add(batch)
    db.flush()
    document = tmp_path / f"{uuid4()}.pdf"
    document.write_bytes(overrides.pop("content", PDF))
    values = {
        "batch_id": batch.id,
        "codice_fiscale": "RSSMRA70A01G113X",
        "display_name": "ROSSI MARIO",
        "years_json": [2021],
        "avviso_ids_json": [],
        "paid_amount": 0,
        "status": "generated",
        "generated_document_path": str(document),
        "payload_json": payload(),
    } | overrides
    item = RuoloTributiReminderBatchItem(**values)
    db.add(item)
    db.flush()
    return item


DRAFT_PAGE = """<table class="table" id="col_invio_dett"><thead><tr><th>Identificativo</th></tr></thead>
<tbody>{rows}</tbody></table>"""
DRAFT_ROW = """<tr class="odd"><td><input type="checkbox" id="{id}" name="invioCheck"></td>
<td><a href="#" onclick="dettaglio('dettaglio.do', '{id}', '')">{id}</a></td><td>{name}</td>
<td>28/10/2026 19:01</td><td><div><span class="counter text-basic">{status}</span></div></td>
<td>{price}</td><td><a onclick="MostraAnteprima(800,600,'anteprimaPostaAR.do', {id});">Raccomandata online</a></td>
<td><a onclick="SubmitDoAction('modifica.do','{id}','')"></a></td><td><a onclick="DeleteInvio('{id}')"></a></td></tr>"""
ARCHIVE_ROW = """<tr><td><a href="#" onclick="SubmitDoAction('dettaglio.do','{id}','_self');" id="idInvio">
{id}</a></td><td>{name}</td><td>29/10/2026 08:00</td><td>&euro;&nbsp;5,43</td>
<td><a onclick="SubmitDoAction('cancellaArchivio.do','{id}','_self');"></a></td></tr>"""
DETAIL_PAGE = """<html><body><input type="hidden" name="idInvio" value="{id}">
<table><tr><td>Nome spedizione</td><td>{name}</td></tr><tr><td>Stato</td><td>Accettato</td></tr>
<tr><td>Data spedizione</td><td>29/10/2026 08:00</td></tr></table>
<table id="destinatario"><tr><th>N.</th><th>Servizio</th><th>Destinatario</th><th>Indirizzo</th><th>Info</th></tr>
<tr><td>1</td><td>Raccomandata online AR</td><td>ROSSI MARIO</td><td>VIA CAGLIARI 170 09170 ORISTANO OR</td>
<td>Raccomandata N. 619591492509</td></tr></table><p>Totale &euro;&nbsp;5,43</p></body></html>"""


def draft_page(*rows: dict) -> str:
    defaults = {"status": "Prezzato", "price": "&euro;&nbsp;5,43"}
    return DRAFT_PAGE.format(rows="".join(DRAFT_ROW.format(**(defaults | row)) for row in rows))


def archive_page(*rows: dict) -> str:
    return DRAFT_PAGE.format(rows="".join(ARCHIVE_ROW.format(**row) for row in rows))
