from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from sqlalchemy import select

from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.services import notice_eligibility as service

from .test_notice_import import api_engine as api_engine
from .test_notice_reconciliation import imported_excel
from .test_notice_register import _avviso
from .test_notice_register_api import api as api


def eligible_item(api):
    doc_id = imported_excel(api)
    with api.session() as db:
        avviso = _avviso(db, year=2022)
        avviso.codice_fiscale_raw = "TESTCF"
        document = db.get(NoticeDocument, UUID(doc_id))
        notification = db.get(NoticeNotification, document.id)
        notification.state = "nessuna_evidenza"
        for position in db.scalars(
            select(NoticePosition).where(NoticePosition.document_id == document.id)
        ):
            if position.tax_year == 2023:
                other = _avviso(db, year=2023)
                position.avviso_id = other.id
            else:
                position.avviso_id = avviso.id
            recovery = db.get(NoticeRecovery, position.id)
            recovery.state, recovery.verified_on, recovery.evidence_reference = (
                "non_affidato_verificato",
                date.today(),
                "Rapporto verificato",
            )
        db.commit()
        return {
            "avviso": SimpleNamespace(
                id=avviso.id, anno_tributario=2022, codice_fiscale_raw="TESTCF"
            ),
            "saldo_amount": Decimal("10.00"),
            "payment_status": "unpaid",
            "calculation_policy": "internal_gaia",
        }, document.id


def test_verified_history_allows_generation_and_rechecked_changes_block(api):
    item, doc_id = eligible_item(api)
    with api.session() as db:
        assert service.eligibility(db, item) == {
            "avviso_id": str(item["avviso"].id),
            "eligible": True,
            "reasons": [],
        }
        assert service.generation_allowed(db, item, True)
        assert not service.generation_allowed(db, item, False)
        item["avviso"].anno_tributario = 2024
        assert service.generation_allowed(db, item, True)
        item["avviso"].anno_tributario = 2022
        recovery = db.scalar(select(NoticeRecovery))
        recovery.state = "da_verificare"
        db.flush()
        assert not service.generation_allowed(db, item, True)
        assert "step_non_liberato" in service.eligibility(db, item)["reasons"]
        db.get(NoticeDocument, doc_id).tax_code = "OTHER"
        position = db.scalar(
            select(NoticePosition).where(NoticePosition.avviso_id == item["avviso"].id)
        )
        position.tax_year = 2021
        db.flush()
        assert {"destinatario_discordante", "annualita_discordante"} <= set(
            service.eligibility(db, item)["reasons"]
        )


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"saldo_amount": None}, "saldo_non_verificato"),
        ({"saldo_amount": float("nan")}, "saldo_non_verificato"),
        ({"saldo_amount": 0}, "saldo_non_esigibile"),
        ({"payment_status": "to_review"}, "saldo_non_esigibile"),
        ({"calculation_policy": "external_recovery"}, "gestione_esterna"),
        ({"workflow_status": "sospeso"}, "posizione_bloccata"),
        ({"mailing_delivery": {"delivery_status": "unknown"}}, "invio_incass_da_riconciliare"),
    ],
)
def test_accounting_and_external_signals_fail_closed(api, changes, reason):
    item, _ = eligible_item(api)
    with api.session() as db:
        assert reason in service.eligibility(db, {**item, **changes})["reasons"]


def test_unknown_history_missing_tax_code_and_orphan_positions_block(api):
    item, doc_id = eligible_item(api)
    with api.session() as db:
        db.get(NoticeDocument, doc_id).source_system = "gaia_reminder"
        db.flush()
        assert "storico_non_verificato" in service.eligibility(db, item)["reasons"]
        item["avviso"].codice_fiscale_raw = None
        assert "destinatario_non_verificato" in service.eligibility(db, item)["reasons"]
        item["avviso"].codice_fiscale_raw = "TESTCF"
        position = db.scalar(select(NoticePosition).where(NoticePosition.tax_year == 2023))
        position.avviso_id = None
        db.flush()
        reasons = service.eligibility(db, item)["reasons"]
        assert {"collegamenti_mancanti", "storici_da_collegare"} <= set(reasons)


def test_pending_attempts_require_reviewed_non_notification_evidence(api):
    item, doc_id = eligible_item(api)
    with api.session() as db:
        notification = db.get(NoticeNotification, doc_id)
        db.add(
            NoticeAttempt(
                document_id=doc_id, source_system="manual", source_key=str(uuid4()), channel="posta"
            )
        )
        db.flush()
        assert "invii_non_chiariti" in service.eligibility(db, item)["reasons"]
        notification.state = "tentativo_senza_notifica"
        db.flush()
        assert "invii_non_chiariti" in service.eligibility(db, item)["reasons"]
        notification.evidence_id = db.scalar(
            select(NoticeEvidence.id).where(NoticeEvidence.document_id == doc_id)
        )
        db.flush()
        assert service.eligibility(db, item)["eligible"]
        notification.state, notification.notified_on = "perfezionata", date.today()
        db.flush()
        assert "notifica_perfezionata" in service.eligibility(db, item)["reasons"]
        db.delete(notification)
        db.flush()
        assert "notifica_da_verificare" in service.eligibility(db, item)["reasons"]


def test_poste_without_register_attempt_and_missing_recovery_are_blocked(api):
    item, _ = eligible_item(api)
    with api.session() as db:
        db.add(
            RuoloTributiRegisteredMail(
                id=uuid4(),
                source_shipment_id="mail",
                recipient_index=0,
                avviso_id=item["avviso"].id,
                raw_payload_json={},
            )
        )
        position = db.scalar(
            select(NoticePosition).where(NoticePosition.avviso_id == item["avviso"].id)
        )
        db.delete(db.get(NoticeRecovery, position.id))
        db.flush()
        assert {"poste_da_importare", "step_non_liberato"} <= set(
            service.eligibility(db, item)["reasons"]
        )


@pytest.mark.parametrize("state", ["da_verificare", "affidato", "chiuso", "revocato"])
def test_generated_documents_do_not_hide_explicit_step_assignments(state):
    assert service._recovery_blocks(SimpleNamespace(state=state), True) == (
        state in {"affidato", "chiuso"}
    )
    assert service._recovery_blocks(None, True)
