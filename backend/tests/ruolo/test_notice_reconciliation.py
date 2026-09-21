from concurrent.futures import ThreadPoolExecutor
from datetime import date
from threading import Barrier
from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from app.modules.ruolo.models import RuoloTributiRegisteredMail
from app.modules.ruolo.notice_import_models import NoticeImportRow
from app.modules.ruolo.notice_import_schemas import ConflictDecision, ImportSnapshot
from app.modules.ruolo.notice_register_api_schemas import ReconciliationInput
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticeRecovery,
)
from app.modules.ruolo.notice_register_schemas import OperatorChange
from app.modules.ruolo.services import notice_reconciliation as service
from app.modules.ruolo.services.notice_import import confirm_import, stage_import
from app.modules.ruolo.services.notice_import_conflicts import resolve_conflict
from app.modules.ruolo.services.notice_import_excel import parse_excel
from app.modules.ruolo.services.notice_import_poste import snapshot_poste
from app.modules.ruolo.services.notice_register import RegisterConflict

from .test_notice_import import URL as IMPORT_URL
from .test_notice_import import _metadata, confirm, preview, rows, values, workbook
from .test_notice_import import api_engine as api_engine
from .test_notice_register_api import (
    URL,
    _add_position,
    _create,
    _detail,
    _headers,
    _request,
    _seed_auth,
)
from .test_notice_register_api import api as api


def imported_excel(api):
    batch = preview(api)
    assert confirm(api, batch).status_code == 200
    return rows(api, batch)[0]["document_id"]


def imported_poste(api):
    with api.session() as db:
        db.add(
            RuoloTributiRegisteredMail(
                id=uuid4(),
                source_shipment_id=str(uuid4()),
                recipient_index=0,
                tracking_number="POSTE-TRACK",
                status_label="Servizio erogato",
                raw_payload_json={"original": "poste"},
            )
        )
        db.commit()
    batch = api.client.post(f"{IMPORT_URL}/poste").json()
    assert confirm(api, batch).status_code == 200
    return rows(api, batch)[-1]["document_id"], batch


def reconciliation(api, source, target, **overrides):
    return api.client.post(
        f"{URL}/{source}/riconciliazione",
        json=_request(
            {
                "target_document_id": target,
                "target_version": _detail(api, target)["version"],
                "confirmed": True,
                **overrides,
            },
            _detail(api, source)["version"],
        ),
    )


def conflict(api):
    doc = imported_excel(api)
    batch = preview(api, workbook([values(H="Variante documentata")]))
    assert confirm(api, batch).status_code == 200
    row = rows(api, batch)[0]
    return doc, batch, row


def resolve(api, doc, batch, row, **overrides):
    return api.client.post(
        f"{IMPORT_URL}/{batch['id']}/righe/{row['id']}/risoluzione",
        json=_request(
            {
                "document_id": doc,
                "fingerprint": row["fingerprint"],
                "decision": "keep_existing",
                "confirmed": True,
                **overrides,
            },
            _detail(api, doc)["version"],
        ),
    )


def test_reconcile_moves_events_preserves_originals_and_invalidates_reviews(api):
    target = imported_excel(api)
    source, batch = imported_poste(api)
    before_source, before_target = _detail(api, source), _detail(api, target)
    with api.session() as db:
        for doc_id in (source, target):
            evidence = db.scalar(
                select(NoticeEvidence).where(NoticeEvidence.document_id == UUID(doc_id))
            )
            notification = db.get(NoticeNotification, UUID(doc_id))
            notification.state = "perfezionata"
            notification.notified_on = date.today()
            notification.evidence_id = evidence.id
        recovery = db.scalar(select(NoticeRecovery))
        recovery.state, recovery.verified_on = "affidato", date.today()
        recovery.evidence_reference, recovery.case_reference = "report", "STEP-1"
        db.commit()
    response = reconciliation(api, source, target)
    assert response.status_code == 200, response.text
    assert response.json() == {"document_id": target, "resource_id": source, "version": 2}
    after_source, after_target = _detail(api, source), _detail(api, target)
    assert after_source["reconciled_into_id"] == target
    assert after_source["anomalies"] == []
    assert after_source["original_json"] == before_source["original_json"]
    assert after_target["original_json"] == before_target["original_json"]
    assert (
        after_source["notification_state"] == after_target["notification_state"] == "da_verificare"
    )
    assert {p["recovery"]["state"] for p in after_target["positions"]} == {"da_verificare"}
    assert api.client.get(f"{URL}/{source}/evidenze").json()["total"] == 0
    assert api.client.get(f"{URL}/{target}/evidenze").json()["total"] == 2
    assert api.client.get(f"{URL}/{target}/invii").json()["total"] == 1
    for doc_id in (source, target):
        audit = api.client.get(f"{URL}/{doc_id}/storico").json()["items"][0]
        assert audit["action"] == "reconcile_poste"
        assert audit["actor_id"] == 1
        assert audit["before_json"]["source_notification"]["state"] == "perfezionata"
        assert audit["after_json"]["target_id"] == target
    assert api.client.get(URL).json()["total"] == 1
    assert api.client.get(URL, params={"view": "riconciliati"}).json()["items"][0]["id"] == source
    assert api.client.get(URL, params={"q": "POSTE-TRACK"}).json()["items"][0]["id"] == target
    assert rows(api, batch)[0]["document_id"] == source
    assert reconciliation(api, source, target).status_code == 409
    assert (
        api.client.post(
            f"{URL}/{source}/posizioni",
            json=_request(
                {
                    "source_namespace": "incass",
                    "source_reference": "x",
                    "tax_year": 2022,
                },
                2,
            ),
        ).status_code
        == 409
    )
    with api.session() as db:
        assert db.scalar(select(NoticeAttempt)).document_id == UUID(target)
        poste_evidence = db.scalar(
            select(NoticeEvidence).where(NoticeEvidence.source_system == "poste_db")
        )
        assert poste_evidence.attempt_id == db.scalar(select(NoticeAttempt.id))


def test_reconciliation_candidate_search_and_rejections(api):
    target = imported_excel(api)
    source, _ = imported_poste(api)
    empty = _create(api)
    candidates = api.client.get(URL, params={"reconciliation_candidates": True}).json()
    assert [item["id"] for item in candidates["items"]] == [target]
    assert reconciliation(api, source, source).status_code == 422
    assert reconciliation(api, target, source).status_code == 422
    assert reconciliation(api, source, empty).status_code == 422
    assert reconciliation(api, source, target, target_version=99).status_code == 409
    assert reconciliation(api, source, target, confirmed=False).status_code == 422
    _add_position(api, source)
    assert reconciliation(api, source, target).status_code == 422


def test_poste_target_is_rejected_even_with_positions(api):
    source, _ = imported_poste(api)
    target = _create(
        api, positions=[{"source_namespace": "x", "source_reference": "y", "tax_year": 2022}]
    )
    with api.session() as db:
        db.get(NoticeDocument, UUID(target)).source_system = "poste_db"
        db.commit()
    assert reconciliation(api, source, target).status_code == 422


def test_reconciliation_rollback_after_transfer(api, monkeypatch):
    target = imported_excel(api)
    source, _ = imported_poste(api)
    original = service._audit

    def fail(db, document, change, event):
        original(db, document, change, event)
        raise ValueError("Errore simulato dopo trasferimento")

    monkeypatch.setattr(service, "_audit", fail)
    assert reconciliation(api, source, target).status_code == 422
    assert _detail(api, source)["reconciled_into_id"] is None
    assert api.client.get(f"{URL}/{source}/invii").json()["total"] == 1
    assert api.client.get(f"{URL}/{target}/evidenze").json()["total"] == 1
    assert _detail(api, source)["version"] == _detail(api, target)["version"] == 1


@pytest.mark.parametrize("decision", ["keep_existing", "register_evidence"])
def test_conflict_decision_is_audited_once_without_overwriting(api, decision):
    doc, batch, row = conflict(api)
    before = _detail(api, doc)
    with api.session() as db:
        notification = db.get(NoticeNotification, UUID(doc))
        notification.state = "perfezionata"
        notification.notified_on = date.today()
        notification.evidence_id = db.scalar(select(NoticeEvidence.id))
        db.commit()
    result = resolve(api, doc, batch, row, decision=decision)
    assert result.status_code == 200, result.text
    after = _detail(api, doc)
    assert after["original_json"] == before["original_json"]
    assert after["positions"] == before["positions"]
    assert after["document_number"] == before["document_number"]
    assert after["version"] == 2
    expected_state = "perfezionata" if decision == "keep_existing" else "da_verificare"
    assert after["notification_state"] == expected_state
    resolved = rows(api, batch)[0]
    assert resolved["outcome"] == "conflict"
    assert resolved["payload"] == row["payload"]
    assert resolved["resolution"]["decision"] == decision
    assert resolved["resolution"]["actor_id"] == 1
    assert resolved["resolution"]["reason"] == "Verifica fascicolo cartaceo"
    assert resolved["resolution"]["document_version"] == 2
    audit = api.client.get(f"{URL}/{doc}/storico").json()["items"][0]
    assert audit["after_json"]["row_id"] == row["id"]
    assert audit["action"] == "resolve_import_conflict"
    assert api.client.get(f"{IMPORT_URL}/{batch['id']}/righe?review=open").json()["total"] == 0
    assert api.client.get(f"{IMPORT_URL}/{batch['id']}/righe?review=resolved").json()["total"] == 1
    assert resolve(api, doc, batch, row).status_code == 409
    with api.session() as db:
        if decision == "register_evidence":
            evidence = db.get(NoticeEvidence, UUID(resolved["resolution"]["evidence_id"]))
            assert evidence.original_json["payload"] == row["payload"]
        assert db.scalar(select(func.count()).select_from(NoticeAudit)) == 2


def test_conflict_guards_and_preview_are_fail_closed(api):
    doc, batch, row = conflict(api)
    url = f"{IMPORT_URL}/{batch['id']}/righe/{row['id']}/risoluzione"
    payload = {
        "decision": "keep_existing",
        "fingerprint": row["fingerprint"],
        "document_id": doc,
        "confirmed": True,
    }
    assert api.client.post(url, json=_request(payload, 99)).status_code == 409
    assert resolve(api, doc, batch, row, fingerprint="stale").status_code == 409
    assert resolve(api, doc, batch, row, document_id=str(uuid4())).status_code == 409
    assert resolve(api, doc, batch, row, confirmed=False).status_code == 422
    assert resolve(api, doc, batch, row, decision="overwrite").status_code == 422
    assert api.client.post(url, json={**_request(payload), "reason": "  "}).status_code == 422
    assert resolve(api, doc, batch, {**row, "id": str(uuid4())}).status_code == 404
    assert resolve(api, doc, {**batch, "id": str(uuid4())}, row).status_code == 404
    new_batch = preview(api, workbook([values(H="Ancora diversa")]))
    assert resolve(api, doc, new_batch, rows(api, new_batch)[0]).status_code == 409
    with api.session() as db:
        db.get(NoticeImportRow, UUID(row["id"])).outcome = "duplicate"
        db.commit()
    assert resolve(api, doc, batch, row).status_code == 409


@pytest.mark.parametrize("user", [2, 3, 4, 5])
def test_new_commands_require_editor_and_module(api, user):
    _doc, batch, row = conflict(api)
    source, _ = imported_poste(api)
    api.client.headers.update(_headers(user))
    expected = 401 if user == 4 else 403
    for path in (
        f"{URL}/{source}/riconciliazione",
        f"{IMPORT_URL}/{batch['id']}/righe/{row['id']}/risoluzione",
    ):
        assert api.client.post(path, json={}).status_code == expected


def test_poste_reimports_and_conflicts_follow_reconciliation(api):
    target = imported_excel(api)
    source, original_batch = imported_poste(api)
    with api.session() as db:
        mail = db.scalar(select(RuoloTributiRegisteredMail))
        mail.status_label = "Variante prima della riconciliazione"
        db.commit()
    batch = api.client.post(f"{IMPORT_URL}/poste").json()
    assert confirm(api, batch).status_code == 200
    row = rows(api, batch)[0]
    assert row["document_id"] == source
    assert reconciliation(api, source, target).status_code == 200
    response = resolve(api, target, batch, row, decision="register_evidence")
    assert response.status_code == 200, response.text
    assert rows(api, batch)[0]["resolution"]["document_id"] == target
    with api.session() as db:
        mail = db.scalar(select(RuoloTributiRegisteredMail))
        mail.status_label = "Variante dopo la riconciliazione"
        db.commit()
    new_batch = api.client.post(f"{IMPORT_URL}/poste").json()
    assert confirm(api, new_batch).status_code == 200
    assert rows(api, new_batch)[0]["document_id"] == target
    assert rows(api, original_batch)[0]["document_id"] == source
    with api.session() as db:
        assert db.scalar(select(func.count()).select_from(NoticeAttempt)) == 1
        assert db.scalar(select(func.count()).select_from(NoticeDocument)) == 2


def undo(api, source, target, **overrides):
    return api.client.post(
        f"{URL}/{source}/riconciliazione/annulla",
        json=_request(
            {
                "target_document_id": target,
                "target_version": _detail(api, target)["version"],
                "confirmed": True,
                **overrides,
            },
            _detail(api, source)["version"],
        ),
    )


def test_undo_reconciliation_restores_events_without_restoring_assessments(api):
    target = imported_excel(api)
    source, _ = imported_poste(api)
    assert reconciliation(api, source, target).status_code == 200
    result = undo(api, source, target)
    assert result.status_code == 200, result.text
    assert result.json() == {"document_id": source, "resource_id": source, "version": 3}
    assert _detail(api, source)["reconciled_into_id"] is None
    assert _detail(api, source)["notification_state"] == "da_verificare"
    assert api.client.get(f"{URL}/{source}/invii").json()["total"] == 1
    assert api.client.get(f"{URL}/{source}/evidenze").json()["total"] == 1
    assert api.client.get(f"{URL}/{target}/evidenze").json()["total"] == 1
    assert api.client.get(f"{URL}/{target}/invii").json()["total"] == 0
    for doc in (source, target):
        audit = api.client.get(f"{URL}/{doc}/storico").json()["items"][0]
        assert audit["action"] == "undo_reconciliation"
        assert audit["before_json"]["reconciliation_audit_id"]
    assert undo(api, source, target).status_code == 409
    assert reconciliation(api, source, target).status_code == 200


def test_undo_rejects_stale_versions_wrong_target_and_subsequent_edits(api):
    target = imported_excel(api)
    source, _ = imported_poste(api)
    assert undo(api, source, source).status_code == 422
    assert reconciliation(api, source, target).status_code == 200
    assert undo(api, source, target, target_version=99).status_code == 409
    assert undo(api, source, target, confirmed=False).status_code == 422
    _add_position(api, target, reference="new-position")
    assert undo(api, source, target).status_code == 409


def test_undo_rejects_later_reconciliations_and_dependent_imports(api):
    target = imported_excel(api)
    source, batch = imported_poste(api)
    assert reconciliation(api, source, target).status_code == 200
    with api.session() as db:
        record = db.scalar(
            select(NoticeImportRow).where(NoticeImportRow.batch_id == UUID(batch["id"]))
        )
        record.document_id = UUID(target)
        db.commit()
    assert undo(api, source, target).status_code == 409
    with api.session() as db:
        record = db.scalar(
            select(NoticeImportRow).where(NoticeImportRow.batch_id == UUID(batch["id"]))
        )
        record.document_id = UUID(source)
        audit = db.scalar(
            select(NoticeAudit).where(
                NoticeAudit.document_id == UUID(target), NoticeAudit.version == 2
            )
        )
        audit.after_json = {"source_id": str(uuid4())}
        db.commit()
    assert undo(api, source, target).status_code == 409


def test_undo_requires_editor_and_rolls_back_atomic_transfer(api, monkeypatch):
    from app.modules.ruolo.services import notice_reconciliation_undo as undo_service

    target = imported_excel(api)
    source, _ = imported_poste(api)
    assert reconciliation(api, source, target).status_code == 200
    api.client.headers.update(_headers(2))
    assert undo(api, source, target).status_code == 403
    api.client.headers.update(_headers())
    original = undo_service._audit

    def fail(db, document, change, event):
        original(db, document, change, event)
        raise ValueError("Errore simulato dopo annullamento")

    monkeypatch.setattr(undo_service, "_audit", fail)
    assert undo(api, source, target).status_code == 422
    assert _detail(api, source)["reconciled_into_id"] == target
    assert api.client.get(f"{URL}/{target}/invii").json()["total"] == 1


@pytest.fixture
def race_engine(api_engine):
    if api_engine.dialect.name != "postgresql":
        pytest.skip("Concorrenza reale verificata su PostgreSQL")
    schema = f"notice_reconcile_race_{uuid4().hex}"
    with api_engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = create_engine(api_engine.url, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as connection:
            _metadata().create_all(connection)
            _seed_auth(connection)
        yield engine
    finally:
        engine.dispose()
        with api_engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))


def seed_race(engine):
    with Session(engine) as db:
        for index in range(2):
            content = workbook([values(H=f"variant-{index}")])
            parsed, summary = parse_excel(content)
            batch = stage_import(
                db, ImportSnapshot("excel_2022_2023", "a.xlsx", content, parsed, summary), 1
            )
            confirm_import(db, batch.id, batch.digest, 1, "Import")
        row = db.scalar(select(NoticeImportRow).where(NoticeImportRow.outcome == "conflict"))
        target_id, batch_id, row_id, fingerprint = (
            row.document_id,
            row.batch_id,
            row.id,
            row.fingerprint,
        )
        db.add(
            RuoloTributiRegisteredMail(
                id=uuid4(), source_shipment_id="race", recipient_index=0, raw_payload_json={}
            )
        )
        db.flush()
        content, parsed, summary = snapshot_poste(db)
        batch = stage_import(
            db, ImportSnapshot("poste_db", "poste.json", content, parsed, summary), 1
        )
        confirm_import(db, batch.id, batch.digest, 1, "Import")
        source_id = db.scalar(
            select(NoticeDocument.id).where(NoticeDocument.source_system == "poste_db")
        )
        db.commit()
        return source_id, target_id, batch_id, row_id, fingerprint


@pytest.mark.parametrize("operation", ["reconcile", "resolve", "mixed"])
def test_concurrent_decisions_are_serialized(race_engine, operation):
    source_id, target_id, batch_id, row_id, fingerprint = seed_race(race_engine)
    barrier = Barrier(2)
    change = OperatorChange(actor_id=1, reason="Confronto concorrente", expected_version=1)

    def execute(index):
        barrier.wait(timeout=10)
        with Session(race_engine) as db:
            try:
                if operation == "reconcile" or (operation == "mixed" and index == 0):
                    service.reconcile_poste(
                        db,
                        source_id,
                        ReconciliationInput(
                            target_document_id=target_id,
                            target_version=1,
                            confirmed=True,
                        ),
                        change,
                    )
                else:
                    resolve_conflict(
                        db,
                        batch_id,
                        row_id,
                        ConflictDecision(
                            decision="register_evidence",
                            document_id=target_id,
                            fingerprint=fingerprint,
                            confirmed=True,
                        ),
                        change,
                    )
                db.commit()
                return "saved"
            except RegisterConflict:
                db.rollback()
                return "conflict"

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(execute, range(2))) == ["conflict", "saved"]
    with Session(race_engine) as db:
        assert db.get(NoticeDocument, target_id).version == 2
        assert db.scalar(select(func.count()).select_from(NoticeAttempt)) == 1
        assert (
            db.scalar(
                select(func.count())
                .select_from(NoticeAudit)
                .where(
                    NoticeAudit.document_id == target_id,
                    NoticeAudit.version == 2,
                )
            )
            == 1
        )


def test_concurrent_undo_and_import_cannot_leave_a_stale_destination(race_engine):
    from app.modules.ruolo.services.notice_reconciliation_undo import undo_reconciliation

    source_id, target_id, _batch_id, _row_id, _fingerprint = seed_race(race_engine)
    with Session(race_engine) as db:
        service.reconcile_poste(
            db,
            source_id,
            ReconciliationInput(
                target_document_id=target_id,
                target_version=1,
                confirmed=True,
            ),
            OperatorChange(actor_id=1, reason="Confronto", expected_version=1),
        )
        db.scalar(select(RuoloTributiRegisteredMail)).status_label = "Nuovo aggiornamento"
        db.flush()
        content, parsed, summary = snapshot_poste(db)
        batch = stage_import(
            db, ImportSnapshot("poste_db", "new.json", content, parsed, summary), 1
        )
        batch_id, digest = batch.id, batch.digest
        db.commit()
    barrier = Barrier(2)

    def execute(index):
        barrier.wait(timeout=10)
        with Session(race_engine) as db:
            try:
                if index == 0:
                    undo_reconciliation(
                        db,
                        source_id,
                        ReconciliationInput(
                            target_document_id=target_id,
                            target_version=2,
                            confirmed=True,
                        ),
                        OperatorChange(actor_id=1, reason="Rettifica", expected_version=2),
                    )
                else:
                    confirm_import(db, batch_id, digest, 1, "Import aggiornato")
                db.commit()
            except RegisterConflict:
                db.rollback()

    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(execute, range(2)))
    with Session(race_engine) as db:
        source = db.get(NoticeDocument, source_id)
        row = db.scalar(select(NoticeImportRow).where(NoticeImportRow.batch_id == batch_id))
        assert row.document_id == (source.reconciled_into_id or source.id)
