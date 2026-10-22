from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace

import pytest
from sqlalchemy import select
from step_fixtures import add_avviso, scheda, tributo

from app.modules.elaborazioni.step import register_projection
from app.modules.elaborazioni.step.persistence import StoredPdf, persist_scheda
from app.modules.elaborazioni.step.register_projection import desired_recovery, publish_recoveries
from app.modules.elaborazioni.step.ruolo_link import link_documents
from app.modules.ruolo.notice_register_models import (
    NoticeAudit,
    NoticeDocument,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.notice_register_schemas import (
    HistoricalDocument,
    OperatorChange,
    PositionInput,
    RecoveryDecision,
)
from app.modules.ruolo.services import notice_register as register

NOW = datetime(2026, 10, 21, 8, 0, tzinfo=UTC)
CNC = "020190006018040"


def _link(carico: str, pagato: str = "0", discaricato: str = "0"):
    return SimpleNamespace(
        imp_carico=Decimal(carico),
        imp_carico_pagato=Decimal(pagato),
        imp_discaricato=Decimal(discaricato),
    )


def test_desired_recovery_states() -> None:
    open_charge = desired_recovery(
        [(_link("50", "10"), "D2"), (_link("20", "20"), "D1"), (_link("5", "5"), "D1")]
    )
    assert open_charge.state == "affidato" and open_charge.case_reference == "D1, D2"
    assert open_charge.amount == Decimal("75")
    assert desired_recovery([(_link("50", "30", "20"), "D")]).state == "chiuso"
    assert desired_recovery([(_link("50", "0", "50"), "D")]).state == "revocato"
    assert desired_recovery([(_link("0"), "D")]).state == "affidato"
    empty = SimpleNamespace(imp_carico=None, imp_carico_pagato=None, imp_discaricato=None)
    assert desired_recovery([(empty, "D")]).state == "affidato"


def _position(db, avviso_id, *, number: str) -> NoticePosition:
    change = OperatorChange(actor_id=1, reason="Storico di test", expected_version=1)
    document = register.create_historical_document(
        db,
        HistoricalDocument(
            document_number=number,
            positions=[
                PositionInput(source_namespace="test", source_reference=number, tax_year=2019)
            ],
        ),
        change,
    )
    position = db.scalar(select(NoticePosition).where(NoticePosition.document_id == document.id))
    register.link_position(
        db,
        document.id,
        position.id,
        avviso_id,
        change.model_copy(update={"expected_version": document.version}),
    )
    db.commit()
    return position


def _import_step(db, imp_carpag: str = "10,00") -> None:
    rows = [
        tributo("20241421500000003", f"Avv. N. {CNC} Not.", IMP_CAR="50,00", IMP_CARPAG=imp_carpag)
    ]
    result = persist_scheda(
        db,
        scheda(tributi=rows),
        job_id=None,
        now=NOW,
        pdf_store=lambda *_: StoredPdf(status="unavailable", unavailable_reason="test"),
    )
    link_documents(db, list(result.document_ids), now=NOW)
    db.commit()


def _recovery(db, position) -> NoticeRecovery:
    db.expire_all()
    return db.get(NoticeRecovery, position.id)


def test_publish_without_links_is_a_no_op(db) -> None:
    assert publish_recoveries(db, actor_id=1, job_id=1, now=NOW) == dict.fromkeys(
        register_projection.PUBLISH_COUNTERS, 0
    )


def test_publish_projects_step_state_and_respects_operator_decisions(db) -> None:
    avviso_id = add_avviso(db, CNC, 2019)
    owned = _position(db, avviso_id, number="DOC-A")
    operator = _position(db, avviso_id, number="DOC-B")
    reconciled = _position(db, avviso_id, number="DOC-C")
    decided = db.get(NoticeDocument, operator.document_id)
    register.assess_recovery(
        db,
        operator.document_id,
        operator.id,
        RecoveryDecision(
            state="non_affidato_verificato",
            verified_on=NOW.date(),
            evidence_reference="Verifica manuale",
        ),
        OperatorChange(actor_id=1, reason="Verifica operatore", expected_version=decided.version),
    )
    target = db.get(NoticeDocument, owned.document_id)
    db.get(NoticeDocument, reconciled.document_id).reconciled_into_id = target.id
    db.commit()
    add_avviso(db, "020190000000001", 2019)
    _import_step(db)
    orphan = scheda(
        "ORFANO80A01G113X", tributi=[tributo("20241421500000099", "Avv. N. 020190000000001 Not.")]
    )
    orphan["documents"][0]["document"]["NUM_DOC"] = "20241421500000099"
    result = persist_scheda(
        db, orphan, job_id=None, now=NOW, pdf_store=lambda *_: StoredPdf(status="unavailable")
    )
    link_documents(db, list(result.document_ids), now=NOW)
    db.commit()

    counts = publish_recoveries(db, actor_id=1, job_id=7, now=NOW)
    assert counts == {
        "updated": 1,
        "unchanged": 0,
        "operator_decision": 1,
        "conflicts": 0,
        "without_position": 1,
    }
    recovery = _recovery(db, owned)
    assert recovery.state == "affidato" and recovery.case_reference == "20241421500000003"
    assert recovery.amount == Decimal("50.00") and recovery.verified_on == NOW.date()
    assert recovery.evidence_reference.startswith("STEP sync job 7")
    audit = db.scalars(select(NoticeAudit).where(NoticeAudit.action == "assess_recovery")).all()[-1]
    assert audit.actor_id == 1 and "job 7" in audit.reason
    assert _recovery(db, operator).state == "non_affidato_verificato"
    assert _recovery(db, reconciled).state == "da_verificare"

    again = publish_recoveries(db, actor_id=1, job_id=8, now=NOW)
    assert again["unchanged"] == 1 and again["updated"] == 0

    _import_step(db, imp_carpag="50,00")
    paid = publish_recoveries(db, actor_id=1, job_id=9, now=NOW)
    assert paid["updated"] == 1 and _recovery(db, owned).state == "chiuso"


def test_publish_reports_register_conflicts(db, monkeypatch: pytest.MonkeyPatch) -> None:
    avviso_id = add_avviso(db, CNC, 2019)
    position = _position(db, avviso_id, number="DOC-A")
    _import_step(db)

    def conflict(*_args, **_kwargs):
        raise register.RegisterConflict("Registro modificato")

    monkeypatch.setattr(register_projection, "assess_recovery", conflict)
    assert publish_recoveries(db, actor_id=1, job_id=1, now=NOW)["conflicts"] == 1
    assert _recovery(db, position).state == "da_verificare"
