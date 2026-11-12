"""inCASS numbers require exact canonical provenance; reconciled Poste notices stay excluded."""

from uuid import UUID

import pytest
from sqlalchemy import delete, select

from app.modules.communications import ruolo_source, source_validation
from app.modules.communications.policy import Conflict
from app.modules.ruolo.models import (
    RuoloAvviso,
    RuoloTributiNoticeNumber,
    RuoloTributiRegisteredMail,
)
from app.modules.ruolo.notice_register_models import NoticeAttempt, NoticeDocument
from app.modules.ruolo.poste_dispatch_models import PosteDispatchItem, PosteDispatchLot
from app.modules.utenze.models import AnagraficaPaymentNotice, AnagraficaSubject

from .test_template_preview import preview, template

NUMBER = "020210012992910"


def incass(api, monkeypatch):
    AnagraficaPaymentNotice.__table__.create(api.engine, checkfirst=True)
    monkeypatch.setattr(source_validation, "incass_year_checker", lambda db: lambda year: True)
    with api.session() as db:
        db.execute(delete(RuoloTributiNoticeNumber))
        item = ruolo_source.source_item(db, api.source_id)
        subject = AnagraficaSubject(source_name_raw="Synthetic inCASS")
        db.add(subject)
        db.flush()
        item.subject_id = subject.id
        item.payload_json = {**item.payload_json, "notice_number": NUMBER}
        avviso = db.get(RuoloAvviso, UUID(item.avviso_ids_json[0]))
        avviso.codice_cnc = f"01.{NUMBER[:-1]}"
        avviso.subject_id = item.subject_id
        document = db.scalar(
            select(NoticeDocument).where(NoticeDocument.source_system == "gaia_batch_item")
        )
        document.document_number = NUMBER
        notice = AnagraficaPaymentNotice(
            subject_id=item.subject_id,
            source_system="incass",
            source_notice_id=NUMBER,
            codice_fiscale=item.codice_fiscale,
            anno="2021",
        )
        db.add(notice)
        db.commit()
        return notice.id


def test_incass_number_without_gaia_reservation_has_readonly_canonical_provenance(api, monkeypatch):
    incass(api, monkeypatch)
    with api.session() as db:
        source, doc, _, _ = ruolo_source.inspect(db, api.source_id)
        assert source.notice_number_id is None
        assert doc.document_number == NUMBER
        assert db.scalar(select(RuoloTributiNoticeNumber)) is None
    assert preview(api, template(api)).json()["send_blockers"] == []


@pytest.mark.parametrize(
    "change",
    [
        "unknown",
        "cnc",
        "owner",
        "year",
        "identifier",
        "rule",
        "number",
        "empty",
        "multiple",
        "reservation",
        "reservation_state",
    ],
)
def test_unverified_numbers_remain_blocked(api, monkeypatch, change):
    notice_id = incass(api, monkeypatch)
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        notice = db.get(AnagraficaPaymentNotice, notice_id)
        avviso = db.get(RuoloAvviso, UUID(item.avviso_ids_json[0]))
        if change == "unknown":
            db.delete(notice)
        elif change == "cnc":
            avviso.codice_cnc = "01.02021001299292"
        elif change == "owner":
            notice.subject_id = None
        elif change == "year":
            notice.anno = "2022"
        elif change == "identifier":
            notice.codice_fiscale = "DIFFERENT"
        elif change == "rule":
            monkeypatch.setattr(
                source_validation, "incass_year_checker", lambda db: lambda year: False
            )
        elif change == "number":
            item.payload_json = {**item.payload_json, "notice_number": "invalid"}
        elif change == "empty":
            item.avviso_ids_json = []
        elif change == "multiple":
            item.avviso_ids_json = item.avviso_ids_json * 2
        else:
            reservation = RuoloTributiNoticeNumber(
                emission_year=2026,
                progressive=1,
                notice_number="other" if change == "reservation" else NUMBER,
                identity_key="b" * 64,
                status="reserved",
            )
            db.add(reservation)
            db.flush()
            item.notice_number_id = reservation.id
        db.commit()
        with pytest.raises(Conflict):
            ruolo_source.inspect(db, item.id)


@pytest.mark.parametrize("kind", ["register", "dispatch"])
def test_reconciled_poste_is_excluded_even_with_no_active_key(api, kind):
    with api.session() as db:
        item = ruolo_source.source_item(db, api.source_id)
        mail = RuoloTributiRegisteredMail(
            source_shipment_id="9999", recipient_index=0, tracking_number="SYNTHETIC"
        )
        db.add(mail)
        db.flush()
        if kind == "register":
            document = db.scalar(
                select(NoticeDocument).where(NoticeDocument.source_system == "gaia_batch_item")
            )
            db.add(
                NoticeAttempt(
                    document_id=document.id,
                    registered_mail_id=mail.id,
                    source_system="synthetic",
                    source_key="9999",
                    channel="raccomandata",
                    tracking_code="SYNTHETIC",
                )
            )
        else:
            lot = PosteDispatchLot(title="Synthetic", created_by=1, postal_options={})
            db.add(lot)
            db.flush()
            db.add(
                PosteDispatchItem(
                    lot_id=lot.id,
                    batch_item_id=item.id,
                    notice_number=item.payload_json["notice_number"],
                    shipment_name="Synthetic",
                    status="sent",
                    recipient={},
                    artifact_sha256="a" * 64,
                    artifact_size=0,
                    registered_mail_id=mail.id,
                    active_key=None,
                    active_source_key=None,
                )
            )
        db.commit()
        with pytest.raises(Conflict, match="riconciliato con Poste"):
            ruolo_source.inspect(db, item.id)
    result = preview(api, template(api)).json()
    assert result["subject"].startswith("Avviso ")
    assert "riconciliato con Poste" in result["send_blockers"][0]
