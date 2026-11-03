from copy import deepcopy
from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, Table, Uuid, create_engine, event, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.modules.ruolo.campaign_2021_schemas import CampaignApproval
from app.modules.ruolo.notice_draft_models import NoticeDraft
from app.modules.ruolo.notice_register_models import (
    NoticeAttempt,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.router import router
from app.modules.ruolo.services import campaign_2021 as service
from app.modules.ruolo.services import campaign_2021_pdf as pdf
from app.modules.ruolo.services import campaign_2021_read_model as reader
from app.modules.ruolo.services.notice_register import RegisterConflict, RegisterNotFound
from app.modules.utenze.models import AnagraficaPaymentNotice

from .test_campaign_2021 import CF, NUMBER, facts, row, workbook_bytes
from .test_notice_register import _avviso
from .test_notice_register_api import _api_metadata, _headers, _seed_auth

URL = "/ruolo/tributi/campagna-2021"


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False}
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata = _api_metadata()
    Table("ruolo_tributi_reminder_batches", metadata, Column("id", Uuid, primary_key=True))
    for model in (NoticeDraft, AnagraficaPaymentNotice):
        model.__table__.to_metadata(metadata)
    metadata.create_all(engine)
    with engine.connect() as connection:
        _seed_auth(connection)
        connection.commit()
        with Session(connection, expire_on_commit=False) as session:
            yield session
    engine.dispose()


def command(report, **updates):
    return CampaignApproval(
        **(
            {
                "report_sha256": report["report_sha256"],
                "row_number": 2,
                "amount_source": "excel",
                "notification_fee": "0.00",
                "channel": "nessuno",
                "fee_evidence": "Verifica spese sintetica",
                "reason": "Verifica contabile sintetica",
                "confirmed": True,
            }
            | updates
        )
    )


def staged(db, monkeypatch, current=None):
    current = current or facts()
    monkeypatch.setattr(service, "read_positions", lambda db, rows: {NUMBER: deepcopy(current)})
    content = workbook_bytes()
    report = service.analyze(db, content)
    saved = service.stage(db, content, "synthetic.xlsx", report["report_sha256"], 1)
    return saved, content


def test_snapshots_idempotency_freshness_and_no_register_mutations(db, monkeypatch):
    report, content = staged(db, monkeypatch)
    assert service.stage(db, content, "same.xlsx", report["report_sha256"], 1)["id"] == report["id"]
    assert service.list_campaigns(db)[0]["id"] == report["id"]
    with pytest.raises(RegisterConflict):
        service.stage(db, content, "x", "b" * 64, 1)
    monkeypatch.setattr(
        service,
        "build_payload",
        lambda *args: {
            "notice_number": NUMBER,
            "saldo_amount": "106.00",
            "notification_amount": "0.00",
        },
    )
    approved = service.approve(db, UUID(report["id"]), command(report), 1)
    assert service.approve(db, UUID(report["id"]), command(report), 1) == approved
    assert not approved["sent"] and not approved["notified"]
    renders = []
    monkeypatch.setattr(
        service, "render_preview", lambda payload: renders.append(payload) or b"marked-pdf"
    )
    assert service.preview(db, UUID(approved["id"]), 1) == b"marked-pdf"
    assert service.preview(db, UUID(approved["id"]), 1) == b"marked-pdf"
    assert len(renders) == 1
    assert db.scalar(select(func.count()).select_from(NoticeDraft)) == 3
    assert db.scalar(select(func.count()).select_from(NoticeDocument)) == 0
    assert db.scalar(select(func.count()).select_from(NoticeAttempt)) == 0
    monkeypatch.setattr(service, "read_positions", lambda *args: {NUMBER: {"sha256": "b" * 64}})
    with pytest.raises(RegisterConflict, match="cambiati"):
        service.preview(db, UUID(approved["id"]), 1)
    monkeypatch.setattr(service, "code_sha256", lambda: "changed")
    with pytest.raises(RegisterConflict, match="Codice"):
        service.preview(db, UUID(approved["id"]), 1)


def test_approval_gates_and_snapshot_integrity(db, monkeypatch):
    report, _ = staged(db, monkeypatch)
    campaign_id = UUID(report["id"])
    for changes in [
        {"report_sha256": "b" * 64},
        {"row_number": 9999},
        {"notification_fee": "11.55"},
    ]:
        with pytest.raises((RegisterConflict, ValueError)):
            service.approve(db, campaign_id, command(report, **changes), 1)
    record = service.require(db, campaign_id, service.IMPORT)
    original = deepcopy(record.manifest)
    altered = deepcopy(original)
    altered["rows"][0]["reconciliation"]["blockers"] = ["step_non_liberato"]
    record.manifest = altered
    db.flush()
    with pytest.raises(ValueError, match="bloccata"):
        service.approve(db, campaign_id, command(report), 1)
    altered = deepcopy(original)
    altered["rows"][0]["reconciliation"]["reviews"] = ["cf_da_revisionare"]
    record.manifest = altered
    db.flush()
    with pytest.raises(ValueError, match="Riferimento"):
        service.approve(db, campaign_id, command(report), 1)
    monkeypatch.setattr(service, "build_payload", lambda *args: {"notice_number": NUMBER})
    approved = service.approve(
        db,
        campaign_id,
        command(
            report, resolutions={"cf_da_revisionare": "Identità verificata su avviso originale"}
        ),
        1,
    )
    assert approved["state"] == "snapshot_contabile_approvato"
    with pytest.raises(RegisterNotFound):
        service.require(db, uuid4(), service.IMPORT)
    with pytest.raises(RegisterNotFound):
        service.require(db, campaign_id, service.APPROVAL)
    record.artifact = b"corrupt"
    db.flush()
    with pytest.raises(RegisterConflict, match="integro"):
        service.require(db, campaign_id, service.IMPORT)


def test_database_unique_constraint_resolves_competing_identical_snapshots(db, monkeypatch):
    first = service._save(
        db, service.IMPORT, "key", {"filename": "x", "summary": {}}, b"original", 1
    )
    find = service._find
    calls = []

    def racing_find(*args):
        calls.append(1)
        return None if len(calls) == 1 else find(*args)

    monkeypatch.setattr(service, "_find", racing_find)
    assert service._save(db, service.IMPORT, "key", {}, b"same", 1).id == first.id
    monkeypatch.setattr(service, "_find", find)
    with pytest.raises(IntegrityError):
        service._save(db, service.IMPORT, "bad-user", {}, b"original", 9999)


def test_exact_number_adapter_and_immutable_current_data(db, monkeypatch):
    avviso = _avviso(db, 2021)
    avviso.codice_cnc = "01." + NUMBER[:-1]
    avviso.codice_fiscale_raw = CF
    avviso.nominativo_raw = "CONTRIBUENTE ESEMPIO"
    notice = AnagraficaPaymentNotice(
        source_system="incass",
        source_notice_id=NUMBER,
        anno="2021",
        codice_fiscale=CF,
        display_name="CONTRIBUENTE ESEMPIO",
        importo_carico="100,00",
        importo_residuo="100,00",
        importo_riscosso="0,00",
        synced_at=datetime.now(UTC),
        raw_detail_json={"partitario": {"avviso": NUMBER}},
    )
    db.add(notice)
    db.flush()
    engine = {key: None for key in reader.ENGINE}
    engine.update(
        capacitas_avviso_code=NUMBER,
        calculation_policy="internal_gaia",
        paid_amount=0,
        saldo_amount=106,
        interest_amount=0,
        surcharge_amount=6,
        calculation_date="2026-11-02",
    )
    monkeypatch.setattr(
        reader.repo,
        "get_tributi_avviso",
        lambda *args: {
            **engine,
            "incass_notice": {"documented_pec_delivery": False},
            "mailing_delivery": None,
        },
    )
    monkeypatch.setattr(reader.repo, "_partite_payload", lambda *args: [])
    monkeypatch.setattr(
        reader.repo, "_notice_print_policy_payload", lambda *args: {"due_date": "2026-12-15"}
    )
    monkeypatch.setattr(reader, "_ambiguous_history", lambda *args: False)
    monkeypatch.setattr(reader, "_step_assigned_avviso_ids", lambda *args: set())
    monkeypatch.setattr(reader, "get_calculation_policy_for_year", lambda *args: None)
    result = reader.read_positions(db, [row()])[NUMBER]
    assert result["avviso_id"] == str(avviso.id) and result["partitario_available"]
    assert result["engine"]["calculation_date"] == "2026-11-02"
    assert "raw_detail_json" not in result and "taxpayer_portal_access" not in result
    missing = row()
    missing["number"] = "020219999999990"
    assert (
        reader.read_positions(db, [missing])[missing["number"]]["match_error"]
        == "numero_incass_assente"
    )
    notice.source_notice_id = "020219999999990"
    db.flush()
    assert (
        reader.read_positions(db, [missing])[missing["number"]]["match_error"]
        == "numero_ruolo_assente_o_ambiguo"
    )
    notice.source_notice_id = NUMBER
    notice.raw_detail_json = None
    notice.synced_at = None
    db.flush()

    class Policy:
        __table__ = SimpleNamespace(columns=[SimpleNamespace(name="name")])
        name = "Policy sintetica"

    monkeypatch.setattr(reader, "get_calculation_policy_for_year", lambda *args: Policy())
    result = reader.read_positions(db, [row()])[NUMBER]
    assert result["policy"] == {"name": "Policy sintetica"} and not result["partitario_available"]


def test_history_keeps_independent_proofs_attempts_and_recovery(db):
    avviso = _avviso(db, 2021)
    document = NoticeDocument(
        source_system="manual",
        source_key="historical",
        document_number=NUMBER,
        tax_code=CF,
        original_json={},
    )
    db.add(document)
    db.flush()
    position = NoticePosition(
        document_id=document.id,
        avviso_id=avviso.id,
        source_namespace="incass",
        source_reference=NUMBER,
        tax_year=2021,
    )
    db.add(position)
    db.flush()
    assert reader.history(db, avviso.id)[0]["notification"] == "da_verificare"
    evidence = NoticeEvidence(
        document_id=document.id,
        source_system="manual",
        source_key="proof",
        kind="ricevuta",
        reference="Archivio sintetico",
        original_json={},
    )
    db.add(evidence)
    db.flush()
    db.add_all(
        [
            NoticeNotification(
                document_id=document.id, state="nessuna_evidenza", evidence_id=evidence.id
            ),
            NoticeRecovery(position_id=position.id, state="da_verificare"),
            NoticeAttempt(
                document_id=document.id, source_system="manual", source_key="attempt", channel="pec"
            ),
        ]
    )
    db.flush()
    result = reader.history(db, avviso.id)[0]
    assert result["evidence"] == "Archivio sintetico" and result["attempts"][0]["channel"] == "pec"


def test_pdf_payload_uses_approved_source_original_number_and_fee_once(db, monkeypatch):
    avviso = _avviso(db, 2021)
    notice = AnagraficaPaymentNotice(
        source_system="incass",
        source_notice_id=NUMBER,
        raw_detail_json={"partitario": {"avviso": NUMBER}},
    )
    db.add(notice)
    db.flush()
    current = facts()
    current.update(avviso_id=str(avviso.id), incass_id=str(notice.id))
    report = {"report_sha256": "a" * 64}
    monkeypatch.setattr(pdf.repo, "_partite_payload", lambda *args: [])
    payload = pdf.build_payload(db, row(), current, command(report), "2026-11-02T00:00:00Z")
    assert payload["notice_number"] == NUMBER and payload["taxpayer_portal_access"] == []
    assert (
        payload["paid_amount"] == "0.00"
        and payload["campaign_2021_snapshot"]["difference"] == "0.00"
    )
    assert pdf.notice_total_amount(payload) == 106
    payload = pdf.build_payload(
        db,
        row(),
        current,
        command(report, amount_source="gaia", notification_fee="11.55", channel="raccomandata"),
        "2026-11-02T00:00:00Z",
    )
    assert pdf.notice_total_amount(payload) == Decimal("117.55")


def test_api_analyze_retain_approve_preview_and_permissions(db, monkeypatch):
    app = FastAPI()
    app.include_router(router, prefix="/ruolo")
    app.dependency_overrides[get_db] = lambda: db
    monkeypatch.setattr(service, "read_positions", lambda *args: {NUMBER: facts()})
    monkeypatch.setattr(service, "build_payload", lambda *args: {"notice_number": NUMBER})
    monkeypatch.setattr(service, "render_preview", lambda payload: b"marked-pdf")
    with TestClient(app) as client:
        assert client.get(URL).status_code == 401
        client.headers.update(_headers(2))
        content = workbook_bytes()
        report = client.post(URL + "/analisi", files={"file": ("synthetic.xlsx", content)}).json()
        assert report["summary"]["rows"] == 1
        assert db.scalar(select(func.count()).select_from(NoticeDraft)) == 0
        assert (
            client.post(
                URL + "/importazioni",
                files={"file": ("x", content)},
                data={"report_sha256": report["report_sha256"]},
            ).status_code
            == 403
        )
        client.headers.update(_headers())
        response = client.post(
            URL + "/importazioni",
            files={"file": ("x", content)},
            data={"report_sha256": report["report_sha256"]},
        )
        assert response.status_code == 201, response.text
        saved = response.json()
        campaign_id = saved["id"]
        assert (
            client.get(URL + "/" + campaign_id).json()["report_sha256"] == report["report_sha256"]
        )
        assert len(client.get(URL).json()) == 1
        response = client.post(
            URL + f"/{campaign_id}/approvazioni", json=command(saved).model_dump()
        )
        assert response.status_code == 201, response.text
        approved = response.json()
        response = client.post(URL + f"/approvazioni/{approved['id']}/anteprima")
        assert (
            response.status_code == 200
            and response.content == b"marked-pdf"
            and response.headers["cache-control"] == "no-store"
        )
        assert client.get(URL + "/" + str(uuid4())).status_code == 404
        assert (
            client.post(URL + "/analisi", files={"file": ("bad.xlsx", b"bad")}).status_code == 422
        )
        assert (
            client.post(
                URL + f"/{campaign_id}/approvazioni",
                json=command(saved, report_sha256="b" * 64).model_dump(),
            ).status_code
            == 409
        )
        for actor in (3, 4):
            client.headers.update(_headers(actor))
            assert client.get(URL).status_code in (401, 403)
