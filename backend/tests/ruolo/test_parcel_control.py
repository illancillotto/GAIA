from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import StaleDataError
from sqlalchemy.pool import StaticPool

from app.api.deps import require_active_user
from app.core.database import get_db
from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.models.catasto import (
    CatastoBatch,
    CatastoDocument,
    CatastoSisterExtraction,
    CatastoVisuraRequest,
)
from app.modules.ruolo.bootstrap import RUOLO_SECTIONS
from app.modules.ruolo.models import RuoloAvviso, RuoloImportJob, RuoloParticella, RuoloPartita
from app.modules.ruolo.parcel_control_models import ParcelControlCase, ParcelControlIndex
from app.modules.ruolo.router import router as module_router
from app.modules.ruolo.routes import parcel_control_routes as routes
from app.modules.ruolo.services import parcel_control_cases as cases
from app.modules.ruolo.services import parcel_control_identity as identity
from app.modules.ruolo.services import parcel_control_index as index
from app.modules.ruolo.services import parcel_control_proposals as proposals
from app.modules.ruolo.services import parcel_control_queries as queries
from app.modules.ruolo.services import parcel_control_visure as visure
from app.services.permission_resolver import Section

PREFIX = "/ruolo/particelle/controllo"
VALID_CF = "RSSMRA80A01H501U"


@pytest.fixture
def workspace():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    db = Session(engine)
    user = ApplicationUser(
        username="control",
        email="control@example.local",
        password_hash="test",
        role="super_admin",
        is_active=True,
    )
    db.add(user)
    db.add_all([Section(**entry) for entry in RUOLO_SECTIONS])
    db.commit()
    app = FastAPI()
    app.include_router(module_router, prefix="/ruolo")
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[require_active_user] = lambda: user
    with TestClient(app) as client:
        yield db, user, client
    db.close()
    engine.dispose()


def command(data=None, version=1, **overrides):
    return {
        "command_id": str(uuid4()),
        "expected_version": version,
        "reason": "Verifica documentata dall'operatore",
        "data": data or {},
        **overrides,
    }


def seed(db, year, parcel="100", cf=VALID_CF, comune="ORISTANO", code="G113", sheet="1"):
    job = RuoloImportJob(
        anno_tributario=year,
        status="completed",
        records_imported=1,
        records_skipped=0,
        records_errors=0,
    )
    db.add(job)
    db.flush()
    notice = RuoloAvviso(
        import_job_id=job.id,
        codice_cnc=str(uuid4()),
        anno_tributario=year,
        codice_fiscale_raw=cf,
        nominativo_raw="ROSSI MARIO",
    )
    db.add(notice)
    db.flush()
    partita = RuoloPartita(
        avviso_id=notice.id, codice_partita="1", comune_nome=comune, comune_codice=code
    )
    db.add(partita)
    db.flush()
    row = RuoloParticella(
        partita_id=partita.id, anno_tributario=year, foglio=sheet, particella=parcel
    )
    db.add(row)
    db.commit()
    return row, partita, notice, job


def analyze(client):
    response = client.post(f"{PREFIX}/analisi", json=command())
    assert response.status_code == 200, response.text
    return response.json()


def practice(db, user, client, year=2020):
    seed(db, year)
    result = analyze(client)
    response = client.post(f"{PREFIX}/{result['items'][0]['id']}/pratica", json=command())
    assert response.status_code == 200, response.text
    return response.json()


def change(client, case, action, data):
    response = client.post(
        f"{PREFIX}/pratiche/{case['id']}/{action}", json=command(data, case["version"])
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_matrix_completeness_normalization_and_refresh(workspace):
    db, _user, client = workspace
    empty = client.get(PREFIX).json()
    assert empty["total"] == 0 and empty["refreshed_at"] is None
    seed(db, 2020, sheet="001", parcel="00100", cf=None)
    seed(db, 2021)
    _, _, _, job = seed(db, 2025, parcel="200")
    result = analyze(client)
    assert result["total"] == 2
    historical = next(item for item in result["items"] if item["reference"]["particella"] == "100")
    assert historical["years"]["2020"] == "present"
    assert historical["years"]["2021"] == "present"
    assert historical["current_presence"] == "not_verifiable"
    certification = command({"source": "inCASS · ruolo integrale verificato"})
    response = client.post(f"{PREFIX}/annualita/2025/certificazione", json=certification)
    assert response.status_code == 200
    assert (
        client.post(f"{PREFIX}/annualita/2025/certificazione", json=certification).status_code
        == 200
    )
    rows = client.get(f"{PREFIX}?view=missing").json()["items"]
    assert rows[0]["current_presence"] == "absent"
    assert rows[0]["cf_anomaly"] is True
    assert client.get(f"{PREFIX}?view=cf").json()["total"] == 1
    assert client.get(f"{PREFIX}?search=ORISTANO&page_size=1").json()["total"] == 2
    assert client.get(f"{PREFIX}?search=%25").json()["total"] == 0
    assert client.get(f"{PREFIX}?page=0").status_code == 422
    job.records_errors = 1
    db.commit()
    assert (
        client.post(
            f"{PREFIX}/annualita/2025/certificazione", json=command({"source": "Fonte"})
        ).status_code
        == 422
    )
    assert analyze(client)["items"][0]["years"]["2025"] in {"present", "not_verifiable"}
    assert (
        client.post(
            f"{PREFIX}/annualita/2025/certificazione", json=command({"source": "Fonte"})
        ).status_code
        == 422
    )


def test_changed_sources_invalidate_absences_in_case_views(workspace):
    db, _user, client = workspace
    assert queries.current_state(db) is None
    case = practice(db, _user, client)
    _, _, _, job = seed(db, 2025, parcel="200")
    analyze(client)
    certification = client.post(
        f"{PREFIX}/annualita/2025/certificazione", json=command({"source": "Ruolo completo"})
    )
    assert certification.status_code == 200
    assert (
        client.get(f"{PREFIX}/pratiche/{case['id']}").json()["current"]["current_presence"]
        == "absent"
    )
    job.records_errors = 1
    db.commit()
    assert (
        client.get(f"{PREFIX}/pratiche/{case['id']}").json()["current"]["current_presence"]
        == "not_verifiable"
    )
    assert (
        client.get(f"{PREFIX}?view=cases").json()["items"][0]["current_presence"]
        == "not_verifiable"
    )


def test_incomplete_identifiers_sections_duplicates_and_removed_sources(workspace):
    db, user, client = workspace
    seed(db, 2020, code=None)
    seed(db, 2021, code=None)
    seed(db, 2021, comune="MASSAMA")
    seed(db, 2020, comune="DONIGALA")
    seed(db, 2020, comune="DONIGALA")
    result = analyze(client)
    assert result["total"] == 4
    assert sum(item["identity_incomplete"] for item in result["items"]) == 2
    assert {item["reference"]["sezione"] for item in result["items"]} == {None, "B", "C"}
    duplicate = next(item for item in result["items"] if item["reference"]["sezione"] == "B")
    assert len(duplicate["occurrences"]) == 2
    assert index.control_state(db, user.id).current_year == 2025
    for row in db.scalars(select(RuoloParticella)):
        db.delete(row)
    db.commit()
    assert analyze(client)["total"] == 0


@pytest.mark.parametrize(
    "value, anomaly",
    [
        (None, "missing"),
        (" ", "missing"),
        ("123", "incomplete"),
        ("123456789012", "incomplete"),
        ("RSSMRA80A01H501X", "invalid"),
        ("ABCDEFGHIJKLMNOA", "invalid"),
        ("12345678901", "invalid"),
        ("01114601006", None),
        (VALID_CF, None),
    ],
)
def test_tax_code_classification(value, anomaly):
    assert identity.tax_code_check(value)["anomaly"] == anomaly


def test_omocodia_and_tokens():
    from app.modules.catasto.services.validation import _EVEN_MAP, _ODD_MAP

    prefix = "RSSMRAU0A01H501"
    checksum = sum(
        (_ODD_MAP if index % 2 == 0 else _EVEN_MAP)[char] for index, char in enumerate(prefix)
    )
    omocodia = prefix + chr(ord("A") + checksum % 26)
    assert identity.tax_code_check(omocodia)["anomaly"] is None
    assert identity.token("0001") == "1"
    assert identity.token("01/A") == "01/A"
    assert identity.token("\uff11\uff12") == "\uff11\uff12"
    assert identity.annual_presence(False, True) == "absent"


def test_case_persistence_idempotency_versions_and_audit(workspace):
    db, user, client = workspace
    case = practice(db, user, client)
    original = case["original"]
    payload = command({"status": "investigating"}, case["version"])
    url = f"{PREFIX}/pratiche/{case['id']}/status"
    response = client.post(url, json=payload)
    assert response.status_code == 200
    assert client.post(url, json=payload).json()["version"] == response.json()["version"]
    assert client.post(url, json=command({"status": "closed"}, 1)).status_code == 409
    assert client.post(url, json={**payload, "data": {"status": "closed"}}).status_code == 422
    loaded = client.get(f"{PREFIX}/pratiche/{case['id']}").json()
    assert loaded["original"] == original and len(loaded["audit"]) == 2
    assert loaded["status"] == "investigating"
    assert client.get(f"{PREFIX}?view=cases").json()["total"] == 1
    loaded = change(client, loaded, "status", {"status": "excluded"})
    assert client.get(f"{PREFIX}?view=closed").json()["total"] == 1
    reopened = client.post(f"{PREFIX}/{case['parcel_id']}/pratica", json=command()).json()
    assert reopened["id"] == case["id"] and reopened["status"] == "excluded"
    assert client.post(f"{PREFIX}/{uuid4()}/pratica", json=command()).status_code == 404
    assert client.get(f"{PREFIX}/pratiche/{uuid4()}").status_code == 404
    assert (
        client.post(url, json=command({"status": "invalid"}, loaded["version"])).status_code == 422
    )
    assert client.post(url, json=command(reason="   ")).status_code == 422


def evidence(kind="document", **values):
    return {
        "kind": kind,
        "source": "Fonte ufficiale",
        "reference": "Documento 1",
        "observed_at": "2025-01-01",
        **values,
    }


def matched_case(client, case):
    case = change(client, case, "evidence", evidence())
    return change(
        client,
        case,
        "match",
        {
            "tax_code": VALID_CF,
            "name": "ROSSI MARIO",
            "subject_kind": "PF",
            "right": "Proprietà",
            "share": "1/1",
            "period": "2025",
            "status": "confirmed",
            "evidence_ids": [case["evidence"][0]["id"]],
        },
    )


def proposal_data(case, **overrides):
    return {
        "year": 2025,
        "kind": "insertion",
        "component": "0648",
        "match_id": case["matches"][0]["id"],
        "evidence_ids": [entry["id"] for entry in case["evidence"]],
        "eligibility_rule": "Delibera da verificare",
        **overrides,
    }


def test_proposals_fail_closed_and_decisions(workspace):
    db, user, client = workspace
    case = matched_case(client, practice(db, user, client))
    case = change(client, case, "proposal", proposal_data(case))
    assert len(case["proposals"]) == 1
    case = change(client, case, "proposal", proposal_data(case))
    assert len(case["proposals"]) == 1
    proposal_id = case["proposals"][0]["id"]
    data = {"proposal_id": proposal_id, "status": "confirmed"}
    url = f"{PREFIX}/pratiche/{case['id']}/decision"
    assert client.post(url, json=command(data, case["version"])).status_code == 422
    case = change(
        client,
        case,
        "evidence",
        evidence(
            "territory",
            result="inside_outside_town",
            version="2025",
            scope="Consorzio e centri abitati",
        ),
    )
    case = change(client, case, "evidence", evidence("cadastre", result="existing"))
    case = change(client, case, "decision", {"proposal_id": proposal_id, "status": "investigating"})
    assert case["proposals"][0]["status"] == "investigating"
    assert client.get(f"{PREFIX}?view=proposals").json()["total"] == 1
    case = change(client, case, "proposal", proposal_data(case))
    case = change(client, case, "decision", data)
    assert case["proposals"][0]["status"] == "confirmed"
    assert (
        db.get(
            RuoloAvviso, UUID(case["original"]["occurrences"][0]["avviso_id"])
        ).codice_fiscale_raw
        == VALID_CF
    )
    seed(db, 2025)
    assert client.post(url, json=command(data, case["version"])).status_code == 422


def test_already_in_role_keeps_cf_correction(workspace):
    db, user, client = workspace
    case = practice(db, user, client, 2025)
    notice = db.get(RuoloAvviso, UUID(case["original"]["occurrences"][0]["avviso_id"]))
    notice.codice_fiscale_raw = "123"
    db.commit()
    assert analyze(client)["items"][0]["cf_anomaly"]
    case = matched_case(client, client.get(f"{PREFIX}/pratiche/{case['id']}").json())
    url = f"{PREFIX}/pratiche/{case['id']}/proposal"
    assert client.post(url, json=command(proposal_data(case), case["version"])).status_code == 422
    result = client.post(
        url, json=command(proposal_data(case, kind="rectification"), case["version"])
    )
    assert result.status_code == 200
    assert result.json()["proposals"][0]["kind"] == "rectification"


@pytest.mark.parametrize(
    "action,data",
    [
        ("evidence", evidence("unknown")),
        ("evidence", {"kind": "document"}),
        ("evidence", evidence("territory")),
        ("evidence", evidence(parcel_id=str(uuid4()))),
        ("match", {"tax_code": "123"}),
        ("match", {"tax_code": VALID_CF}),
        ("link_visura", {"request_id": str(uuid4())}),
        ("proposal", {"year": 2010}),
        ("proposal", {"year": 2025}),
        ("decision", {"proposal_id": str(uuid4())}),
    ],
)
def test_invalid_commands_are_rejected(workspace, action, data):
    db, user, client = workspace
    case = practice(db, user, client)
    response = client.post(f"{PREFIX}/pratiche/{case['id']}/{action}", json=command(data))
    assert response.status_code == 422, response.text


def make_visura(db, user, mode="soggetto", status="completed", extraction=True):
    batch = CatastoBatch(user_id=user.id, total_items=1)
    db.add(batch)
    db.flush()
    request = CatastoVisuraRequest(
        batch_id=batch.id, user_id=user.id, row_index=1, search_mode=mode, status=status
    )
    db.add(request)
    db.flush()
    document = CatastoDocument(
        user_id=user.id,
        request_id=request.id,
        search_mode=mode,
        tipo_visura="Sintetica",
        filename="visura.pdf",
        filepath="/tmp/visura.pdf",
        catasto="Terreni",
    )
    db.add(document)
    db.flush()
    parsed = None
    if extraction:
        parsed = CatastoSisterExtraction(
            document_id=document.id,
            parser_version="1",
            status="parsed",
            pdf_sha256="a" * 64,
            payload_json={
                "comune_nome": "ORISTANO",
                "comune_codice": "G113",
                "parcel": {"foglio": "1", "particella": "200"},
                "owners": [],
            },
        )
        db.add(parsed)
    db.commit()
    return request, document, parsed


def test_link_visura_recovery_and_partial_results(workspace):
    db, user, client = workspace
    case = practice(db, user, client)
    request, _document, parsed = make_visura(db, user)
    case = change(
        client, case, "link_visura", {"request_id": str(request.id), "scope": "Oristano Territorio"}
    )
    assert case["visure"][0]["status"] == "completed"
    case = change(
        client, case, "link_visura", {"request_id": str(request.id), "scope": "Oristano Territorio"}
    )
    assert len(case["visure"]) == 1
    case = change(client, case, "recover", {"evidence_id": case["evidence"][0]["id"]})
    assert len(case["parcels"]) == 1
    assert case["parcels"][0]["role_match_status"] == "verification_required"
    case = change(client, case, "recover", {"evidence_id": case["evidence"][0]["id"]})
    assert len(case["parcels"]) == 1
    assert client.get(f"{PREFIX}?view=visure").json()["total"] == 1
    assert client.get(f"{PREFIX}?view=recovered").json()["total"] == 1
    assert (
        queries.index_view(db.get(ParcelControlIndex, UUID(case["parcels"][0]["id"])), None)[
            "first_year"
        ]
        is None
    )
    parsed.payload_json = {"parcel": {}}
    db.commit()
    assert (
        client.post(
            f"{PREFIX}/pratiche/{case['id']}/recover",
            json=command({"evidence_id": case["evidence"][0]["id"]}, case["version"]),
        ).status_code
        == 422
    )


@pytest.mark.parametrize("status", ["failed", "not_found", "skipped"])
def test_visura_technical_statuses_are_not_nonexistence(workspace, status):
    db, user, client = workspace
    case = practice(db, user, client)
    request, _document, _parsed = make_visura(db, user, status=status, extraction=False)
    case = change(client, case, "link_visura", {"request_id": str(request.id), "scope": "Oristano"})
    assert case["visure"][0]["status"] == status
    assert case["current"]["territorial_status"] == "verification_required"
    assert (
        client.post(
            f"{PREFIX}/pratiche/{case['id']}/recover",
            json=command({"evidence_id": case["evidence"][0]["id"]}, case["version"]),
        ).status_code
        == 422
    )


def test_visura_queue_reuses_async_system_and_idempotency(workspace, monkeypatch):
    db, user, client = workspace
    case = practice(db, user, client)
    fake_row = SimpleNamespace(
        search_mode="immobile",
        comune="ORISTANO",
        comune_codice="G113",
        catasto="Terreni",
        sezione=None,
        foglio="1",
        particella="100",
        subalterno=None,
        tipo_visura="Sintetica",
        subject_kind=None,
        subject_id=None,
        request_type="attuale",
        intestazione=None,
        status="pending",
    )
    monkeypatch.setattr(visure, "validate_visure_records", lambda *_args: [fake_row])
    url = f"{PREFIX}/pratiche/{case['id']}/visura/richiesta"
    data = {"scope": "Oristano", "request": {"search_mode": "immobile"}}
    case = client.post(url, json=command(data, case["version"])).json()
    assert len(case["visure"]) == 1 and case["visure"][0]["status"] == "pending"
    case = client.post(url, json=command(data, case["version"])).json()
    assert len(case["visure"]) == 1
    assert (
        client.post(
            url,
            json=command(
                {"scope": "Oristano", "request": {"search_mode": "soggetto"}}, case["version"]
            ),
        ).status_code
        == 422
    )
    case = matched_case(client, case)
    fake_row.search_mode = "soggetto"
    fake_row.subject_id = VALID_CF
    fake_row.subject_kind = "PF"
    response = client.post(
        url,
        json=command(
            {
                "scope": "Oristano",
                "request": {"search_mode": "soggetto"},
                "match_id": case["matches"][0]["id"],
            },
            case["version"],
        ),
    )
    assert response.status_code == 200, response.text
    assert len(response.json()["visure"]) == 2
    fake_row.status = "skipped"
    assert (
        client.post(
            url, json=command({"scope": "Altro", "request": {}}, response.json()["version"])
        ).status_code
        == 422
    )


def test_authorization_and_transaction_conflicts(workspace, monkeypatch):
    db, user, client = workspace
    case = practice(db, user, client)
    user.role = "operator"
    user.module_ruolo = True
    user.module_elaborazioni = False
    db.commit()
    assert client.post(f"{PREFIX}/analisi", json=command()).status_code == 403
    assert (
        client.post(f"{PREFIX}/pratiche/{case['id']}/visura/richiesta", json=command()).status_code
        == 403
    )
    user.module_ruolo = False
    db.commit()
    assert client.get(PREFIX).status_code == 403
    user.role = "super_admin"
    db.commit()
    for exception in (IntegrityError("test", {}, Exception()), StaleDataError("concurrent")):

        def failing(*_args, failure=exception):
            raise failure

        monkeypatch.setattr(routes, "mutate", failing)
        assert (
            client.post(
                f"{PREFIX}/pratiche/{case['id']}/status",
                json=command({"status": "closed"}, case["version"]),
            ).status_code
            == 409
        )


def test_postgres_advisory_lock():
    fake_db = SimpleNamespace(
        get_bind=lambda: SimpleNamespace(dialect=SimpleNamespace(name="postgresql")),
        scalar=lambda _statement: False,
    )
    with pytest.raises(ValueError, match="Analisi già"):
        index.analysis_lock(fake_db)
    fake_db.scalar = lambda _statement: True
    index.analysis_lock(fake_db)


def test_all_anomalous_notices_include_headers_without_parcels(workspace):
    db, _user, client = workspace
    row, partita, notice, _job = seed(db, 2025, cf=None)
    db.delete(row)
    db.delete(partita)
    db.commit()
    response = client.get(f"{PREFIX}/avvisi?search={notice.codice_cnc}")
    assert response.status_code == 200 and response.json()["total"] == 1
    assert client.get(f"{PREFIX}/avvisi").json()["total"] == 1
    assert client.get(f"{PREFIX}/avvisi?search=nonexistent").json()["total"] == 0
    payload = command()
    url = f"{PREFIX}/avvisi/{notice.id}/pratica"
    case = client.post(url, json=payload).json()
    assert case["parcel_id"] is None and case["parcels"] == []
    assert case["current"]["current_presence"] == "not_verifiable"
    assert client.post(url, json=payload).json()["id"] == case["id"]
    assert client.get(f"{PREFIX}?view=cases&search={notice.codice_cnc}").json()["total"] == 1
    case = change(client, case, "evidence", evidence())
    assert case["evidence"][0]["parcel_id"] is None
    assert client.post(f"{PREFIX}/avvisi/{uuid4()}/pratica", json=command()).status_code == 404


def test_notice_case_preserves_all_parcels_and_individual_outcomes(workspace):
    db, _user, client = workspace
    _row, partita, notice, _job = seed(db, 2025, cf="123")
    db.add(
        RuoloParticella(partita_id=partita.id, anno_tributario=2025, foglio="2", particella="200")
    )
    db.add(
        RuoloParticella(partita_id=partita.id, anno_tributario=2025, foglio="2", particella="200")
    )
    db.commit()
    url = f"{PREFIX}/avvisi/{notice.id}/pratica"
    assert client.post(url, json=command()).status_code == 422
    analyze(client)
    case = client.post(url, json=command()).json()
    assert len(case["parcels"]) == 2 and len(case["original"]["occurrences"]) == 3
    case = change(
        client, case, "parcel_status", {"parcel_id": case["parcels"][0]["id"], "status": "excluded"}
    )
    assert [parcel["status"] for parcel in case["parcels"]] == ["excluded", "investigating"]
    assert case["status"] == "open"
    for data in ({"status": "invalid"}, {"parcel_id": str(uuid4()), "status": "excluded"}):
        assert (
            client.post(
                f"{PREFIX}/pratiche/{case['id']}/parcel_status", json=command(data, case["version"])
            ).status_code
            == 422
        )


def test_formal_matching_rejects_unsubstantiated_confirmation(workspace):
    db, user, client = workspace
    case = practice(db, user, client)
    case = change(client, case, "evidence", evidence())
    base = {
        "tax_code": VALID_CF,
        "evidence_ids": [case["evidence"][0]["id"]],
        "status": "confirmed",
        "subject_kind": "PF",
        "name": "Mario",
        "right": "Proprietà",
        "share": "1/1",
        "period": "2025",
    }
    for data in (
        {**base, "status": "invalid"},
        {**base, "name": ""},
        {**base, "subject_kind": "unknown"},
    ):
        assert (
            client.post(
                f"{PREFIX}/pratiche/{case['id']}/match", json=command(data, case["version"])
            ).status_code
            == 422
        )
    with pytest.raises(ValueError, match="Azione non supportata"):
        cases.update_case(db, db.get(ParcelControlCase, UUID(case["id"])), "unknown", {}, user.id)


def test_more_evidence_invalidates_proposal_and_past_requires_historical_title(workspace):
    db, user, client = workspace
    case = matched_case(client, practice(db, user, client))
    case = change(
        client,
        case,
        "evidence",
        evidence("territory", result="inside_outside_town", version="2025", scope="Ufficiale"),
    )
    base = proposal_data(case)
    for data in (
        {**base, "component": ""},
        {**base, "evidence_ids": []},
        {**base, "parcel_id": str(uuid4())},
        {**base, "year": 2021},
    ):
        assert (
            client.post(
                f"{PREFIX}/pratiche/{case['id']}/proposal", json=command(data, case["version"])
            ).status_code
            == 422
        )
    case = change(client, case, "proposal", base)
    decision = {"proposal_id": case["proposals"][0]["id"], "status": "confirmed"}
    url = f"{PREFIX}/pratiche/{case['id']}/decision"
    assert client.post(url, json=command(decision, case["version"])).status_code == 422
    assert (
        client.post(
            url, json=command({**decision, "status": "invalid"}, case["version"])
        ).status_code
        == 422
    )
    case = change(client, case, "evidence", evidence("cadastre", result="existing"))
    assert client.post(url, json=command(decision, case["version"])).status_code == 422
    case = change(client, case, "proposal", proposal_data(case, eligibility_rule=""))
    assert client.post(url, json=command(decision, case["version"])).status_code == 422
    case = change(client, case, "proposal", proposal_data(case))
    case = change(client, case, "decision", decision)
    assert (
        client.post(
            f"{PREFIX}/pratiche/{case['id']}/proposal",
            json=command(proposal_data(case), case["version"]),
        ).status_code
        == 422
    )
    case = change(
        client, case, "proposal", proposal_data(case, year=2021, kind="historical_review")
    )
    historical = next(proposal for proposal in case["proposals"] if proposal["year"] == 2021)
    data = {"proposal_id": historical["id"], "status": "confirmed"}
    assert client.post(url, json=command(data, case["version"])).status_code == 422
    case = change(client, case, "evidence", evidence("historical_title", years=[2021]))
    case = change(
        client, case, "proposal", proposal_data(case, year=2021, kind="historical_review")
    )
    case = change(client, case, "decision", data)
    assert (
        next(proposal for proposal in case["proposals"] if proposal["year"] == 2021)["status"]
        == "confirmed"
    )


def test_territorial_exclusion_and_recovered_role_check(workspace):
    db, user, client = workspace
    case = matched_case(client, practice(db, user, client))
    request, _document, _parsed = make_visura(db, user)
    case = change(client, case, "link_visura", {"request_id": str(request.id), "scope": "Oristano"})
    case = change(client, case, "recover", {"evidence_id": case["evidence"][-1]["id"]})
    recovered_id = case["parcels"][0]["id"]
    data = proposal_data(case, parcel_id=recovered_id)
    assert (
        client.post(
            f"{PREFIX}/pratiche/{case['id']}/proposal", json=command(data, case["version"])
        ).status_code
        == 422
    )
    case = change(
        client,
        case,
        "evidence",
        evidence("role_check", parcel_id=recovered_id, result="absent", years=[2025]),
    )
    rejected = client.post(
        f"{PREFIX}/pratiche/{case['id']}/proposal",
        json=command(proposal_data(case, parcel_id=recovered_id), case["version"]),
    )
    assert rejected.status_code == 422 and "2011-2025" in rejected.json()["detail"]
    case = change(
        client,
        case,
        "evidence",
        evidence("role_check", parcel_id=recovered_id, result="present", years=[2011]),
    )
    case = change(client, case, "proposal", proposal_data(case, parcel_id=recovered_id))
    assert len(case["proposals"]) == 1
    with pytest.raises(ValueError, match="Verifica territoriale"):
        proposals.verify_territory([evidence("territory", result="inside_town")])
    with pytest.raises(ValueError, match="Verifica territoriale"):
        proposals.verify_territory([evidence("territory", result="outside")])


@pytest.mark.parametrize("code", ["FD", " FD_1 ", "fd_2", "FD_3", "FD_4", "FD_5", "FD_6", "FD_7"])
def test_fd_districts_cannot_be_confirmed(code):
    with pytest.raises(ValueError, match="FD escluso"):
        proposals.verify_territory(
            [evidence("territory", result="inside_outside_town", district_code=code)]
        )


def test_history_starts_in_2011_and_missing_years_are_unknown(workspace):
    db, _user, client = workspace
    seed(db, 2010, parcel="999")
    seed(db, 2011)
    seed(db, 2019)
    result = analyze(client)
    assert result["total"] == 1
    item = result["items"][0]
    assert set(item["years"]) == {str(year) for year in range(2011, 2026)}
    assert item["first_year"] == 2011 and item["last_year"] == 2019
    assert item["years"]["2011"] == item["years"]["2019"] == "present"
    assert item["years"]["2012"] == "not_verifiable"
    assert (
        client.post(
            f"{PREFIX}/annualita/2011/certificazione",
            json=command({"source": "Ruolo 2011 verificato"}),
        ).status_code
        == 200
    )
    case = client.post(f"{PREFIX}/{item['id']}/pratica", json=command()).json()
    for result in ("inside_town", "partially_inside_town"):
        case = change(
            client,
            case,
            "evidence",
            evidence("territory", result=result, scope="Centro abitato", version="ufficiale"),
        )
        assert case["status"] == "open"
        assert case["current"]["first_year"] == 2011


def test_missing_sources_and_visure_guards(workspace):
    db, user, client = workspace
    for year, source in ((2019, "Fonte"), (2020, ""), (2020, "Fonte")):
        assert (
            client.post(
                f"{PREFIX}/annualita/{year}/certificazione", json=command({"source": source})
            ).status_code
            == 422
        )
    case = practice(db, user, client)
    with pytest.raises(ValueError, match="Visura non trovata"):
        queries.visura_view(db, uuid4())
    for action, data in (("recover", {}), ("visura/richiesta", {})):
        assert (
            client.post(
                f"{PREFIX}/pratiche/{case['id']}/{action}", json=command(data, case["version"])
            ).status_code
            == 422
        )
    request, document, _parsed = make_visura(db, user)
    assert (
        client.post(
            f"{PREFIX}/pratiche/{case['id']}/link_visura",
            json=command({"request_id": str(request.id)}, case["version"]),
        ).status_code
        == 422
    )
    assert queries.visura_view(db, request.id)["document_id"] == str(document.id)
    for job in db.scalars(select(RuoloImportJob)):
        job.records_skipped = None
    db.commit()
    analyze(client)
    assert (
        client.post(
            f"{PREFIX}/annualita/2020/certificazione", json=command({"source": "Fonte"})
        ).status_code
        == 422
    )


def test_incoherent_cf_evidence_is_preserved(workspace):
    db, _user, client = workspace
    _row, partita, notice, _job = seed(db, 2025)
    partita.contribuente_cf = "01114601006"
    db.commit()
    result = analyze(client)
    assert result["items"][0]["cf_anomaly"] is True
    assert result["items"][0]["occurrences"][0]["tax_code"]["anomaly"] == "inconsistent"
    headers = client.get(f"{PREFIX}/avvisi").json()
    assert headers["total"] == 1
    assert headers["notices"][0]["tax_code"]["anomaly"] == "inconsistent"
    opened = client.post(f"{PREFIX}/avvisi/{notice.id}/pratica", json=command()).json()
    assert opened["original"]["notice"]["tax_code"]["anomaly"] == "inconsistent"
    partita.contribuente_cf = VALID_CF
    db.commit()
    assert client.get(f"{PREFIX}/avvisi").json()["total"] == 0


def test_replay_analysis_opening_and_visura_version_conflict(workspace, monkeypatch):
    db, user, client = workspace
    seed(db, 2025)
    payload = command()
    first = client.post(f"{PREFIX}/analisi", json=payload).json()
    assert (
        client.post(f"{PREFIX}/analisi", json=payload).json()["refreshed_at"]
        == first["refreshed_at"]
    )
    parcel_id = first["items"][0]["id"]
    payload = command()
    case = client.post(f"{PREFIX}/{parcel_id}/pratica", json=payload).json()
    assert client.post(f"{PREFIX}/{parcel_id}/pratica", json=payload).json()["id"] == case["id"]
    case = change(client, case, "status", {"status": "investigating"})
    url = f"{PREFIX}/pratiche/{case['id']}/visura/richiesta"
    assert client.post(url, json=command({}, 1)).status_code == 409
    request, _document, _parsed = make_visura(db, user, mode="immobile")
    payload = command({"scope": "Oristano"}, case["version"])

    def queued(_db, _case, _data, _actor):
        cases.link_visura(_db, _case, {"request_id": str(request.id), "scope": "Oristano"}, _actor)

    monkeypatch.setattr(visure, "queue_visura", queued)
    response = client.post(url, json=payload)
    assert response.status_code == 200
    assert client.post(url, json=payload).json()["version"] == response.json()["version"]


def test_changing_sources_cannot_publish_a_mixed_analysis(workspace, monkeypatch):
    db, _user, client = workspace
    seed(db, 2025)
    monkeypatch.setattr(index, "source_stamp", lambda _db: next(stamps))
    stamps = iter(["before", "after"])
    response = client.post(f"{PREFIX}/analisi", json=command())
    assert response.status_code == 422 and "cambiati durante" in response.json()["detail"]


def test_migration_roundtrip_matches_runtime_schema():
    import importlib.util
    from pathlib import Path

    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    path = Path(__file__).parents[2] / "alembic/versions/20261006_1200_ruolo_parcel_control.py"
    spec = importlib.util.spec_from_file_location("control_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        context = MigrationContext.configure(connection)
        with Operations.context(context):
            migration.upgrade()
            inspector = inspect(connection)
            names = inspector.get_table_names()
            assert len(names) == 5
            for name in names:
                columns = {column["name"] for column in inspector.get_columns(name)}
                assert columns == set(Base.metadata.tables[name].columns.keys())
            migration.downgrade()
            assert inspect(connection).get_table_names() == []
    engine.dispose()
