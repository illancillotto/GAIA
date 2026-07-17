from __future__ import annotations

from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser
from app.models.catasto import CatastoComune
from app.models.catasto_phase1 import CatAdeParticella, CatCapacitasGridRow, CatCapacitasGridSnapshot, CatParticella
from app.models.elaborazioni import ElaborazioneCredential, ElaborazioneBatch, ElaborazioneRichiesta
from app.models.section_permission import RoleSectionPermission, Section
from app.modules.riordino.models import (
    RiordinoDocumentTypeConfig,
    RiordinoIssue,
    RiordinoIssueTypeConfig,
    RiordinoPhase,
    RiordinoPractice,
    RiordinoStep,
    RiordinoStepTemplate,
)
from app.modules.riordino.schemas.block import BlockCreate
from app.modules.riordino.services.block_service import _ade_query_for_selection, complete_sister_visura, review_block_parcel
from app.modules.riordino.services import ensure_demo_practices
from app.modules.utenze.models import AnagraficaSubject

SECTION_KEYS = [
    ("riordino.dashboard", "Dashboard Riordino", "riordino", "viewer", 10),
    ("riordino.practices", "Pratiche Riordino", "riordino", "viewer", 20),
    ("riordino.workflow", "Workflow Riordino", "riordino", "viewer", 30),
    ("riordino.appeals", "Ricorsi Riordino", "riordino", "viewer", 40),
    ("riordino.issues", "Issue Riordino", "riordino", "viewer", 50),
    ("riordino.documents", "Documenti Riordino", "riordino", "viewer", 60),
    ("riordino.gis", "GIS Riordino", "riordino", "viewer", 70),
    ("riordino.notifications", "Notifiche Riordino", "riordino", "viewer", 80),
    ("riordino.export", "Export Riordino", "riordino", "reviewer", 85),
    ("riordino.config", "Configurazione Riordino", "riordino", "admin", 90),
]


SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)

client = TestClient(app)


TEMPLATES = [
    ("phase_1", "F1_STUDIO_PIANO", "Studio del Piano", 1, True, None, False, False, None),
    ("phase_1", "F1_INDAGINE", "Indagine", 2, True, None, False, False, None),
    ("phase_1", "F1_ELABORAZIONE", "Elaborazione", 3, True, None, False, False, None),
    ("phase_1", "F1_PUBBLICAZIONE", "Pubblicazione", 4, True, None, True, False, None),
    ("phase_1", "F1_OSSERVAZIONI", "Osservazioni", 5, True, None, False, True, ["ricorsi_presenti", "nessun_ricorso"]),
    ("phase_1", "F1_RICORSI", "Ricorsi", 6, False, None, True, False, None),
    ("phase_1", "F1_COMMISSIONE", "Commissione", 7, False, None, True, False, None),
    ("phase_1", "F1_RISOLUZIONE", "Risoluzione", 8, True, None, True, False, None),
    ("phase_1", "F1_TRASCRIZIONE", "Trascrizione", 9, True, None, True, False, None),
    ("phase_1", "F1_CONSERVATORIA", "Conservatoria", 10, True, None, True, False, None),
    ("phase_1", "F1_VOLTURA", "Voltura", 11, True, None, True, False, None),
    ("phase_1", "F1_CARICAMENTO", "Caricamento", 12, True, None, False, False, None),
    ("phase_1", "F1_OUTPUT", "Output", 13, True, None, False, False, None),
    ("phase_2", "F2_SCARICO_DATI", "Scarico dati", 1, True, None, False, False, None),
    ("phase_2", "F2_CSV", "CSV", 2, True, None, True, False, None),
    ("phase_2", "F2_VERIFICA", "Verifica", 3, True, None, False, True, ["conforme", "non_conforme"]),
    ("phase_2", "F2_ESTRATTO_MAPPA", "Estratto mappa", 4, True, None, True, False, None),
    ("phase_2", "F2_FUSIONE", "Fusione", 5, False, "anomalia", True, False, None),
    ("phase_2", "F2_DOCTE", "DOCTE", 6, False, "anomalia", True, False, None),
    ("phase_2", "F2_PREGEO", "PREGEO", 7, True, None, True, False, None),
    ("phase_2", "F2_MAPPALE_UNITO", "Mappale unito", 8, True, None, True, False, None),
    ("phase_2", "F2_RIPRISTINO", "Ripristino", 9, False, "anomalia", False, False, None),
    ("phase_2", "F2_ATTI_RT", "Atti RT", 10, True, None, True, False, None),
    ("phase_2", "F2_AGG_GIS", "Agg GIS", 11, True, None, False, False, None),
    ("phase_2", "F2_DOCUMENTO_FINALE", "Documento finale", 12, True, None, True, False, None),
]


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_database(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Generator[None, None, None]:
    monkeypatch.setenv("GAIA_RIORDINO_STORAGE_ROOT", str(tmp_path / "riordino"))
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username="admin",
            email="admin@example.local",
            password_hash=hash_password("secret123"),
            role="admin",
            is_active=True,
            module_riordino=True,
        )
    )
    db.add_all(
        [
            ApplicationUser(
                username="coordinator",
                email="coordinator@example.local",
                password_hash=hash_password("secret123"),
                role="reviewer",
                is_active=True,
                module_riordino=True,
            ),
            ApplicationUser(
                username="operator",
                email="operator@example.local",
                password_hash=hash_password("secret123"),
                role="viewer",
                is_active=True,
                module_riordino=True,
            ),
        ]
    )
    subject = AnagraficaSubject(
        source_name_raw="Soggetto test",
        subject_type="person",
        status="active",
    )
    db.add(subject)
    db.add(
        RiordinoDocumentTypeConfig(
            code="decreto",
            label="Decreto",
            description="Documento decreto",
            sort_order=10,
            is_active=True,
        )
    )
    db.add(
        RiordinoIssueTypeConfig(
            code="anomalia_documentale",
            label="Anomalia documentale",
            category="documentary",
            default_severity="medium",
            description="Problema documentale",
            sort_order=10,
            is_active=True,
        )
    )
    for key, label, module, min_role, sort_order in SECTION_KEYS:
        section = Section(
            module=module,
            key=key,
            label=label,
            min_role=min_role,
            is_active=True,
            sort_order=sort_order,
        )
        db.add(section)
        db.flush()
        for role, is_granted in (
            ("super_admin", True),
            ("admin", True),
            ("reviewer", min_role in {"viewer", "reviewer"}),
            ("viewer", min_role == "viewer"),
        ):
            db.add(
                RoleSectionPermission(
                    section_id=section.id,
                    role=role,
                    is_granted=is_granted,
                    updated_by_id=None,
                )
            )
    for phase_code, code, title, seq, is_required, branch, requires_document, is_decision, outcome_options in TEMPLATES:
        db.add(
            RiordinoStepTemplate(
                phase_code=phase_code,
                code=code,
                title=title,
                sequence_no=seq,
                is_required=is_required,
                branch=branch,
                requires_document=requires_document,
                is_decision=is_decision,
                outcome_options=outcome_options,
                is_active=True,
            )
        )
    db.add(CatastoComune(nome="Comune Test", codice_sister="H501#COMUNE TEST#0#0"))
    db.add(
        ElaborazioneCredential(
            user_id=3,
            label="SISTER test",
            sister_username="operator-sister",
            sister_password_encrypted=b"encrypted",
            active=True,
            is_default=True,
        )
    )
    db.commit()
    db.refresh(subject)
    db.close()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def db_session() -> Session:
    return TestingSessionLocal()


def auth_headers() -> dict[str, str]:
    return auth_headers_for("admin")


def auth_headers_for(username: str) -> dict[str, str]:
    response = client.post("/auth/login", json={"username": username, "password": "secret123"})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_practice() -> dict:
    response = client.post(
        "/api/riordino/practices",
        headers=auth_headers(),
        json={
            "title": "Pratica test",
            "municipality": "Comune Test",
            "grid_code": "M1",
            "lot_code": "L1",
            "owner_user_id": 1,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


def get_detail(practice_id: str) -> dict:
    response = client.get(f"/api/riordino/practices/{practice_id}", headers=auth_headers())
    assert response.status_code == 200, response.text
    return response.json()


def seed_block_source_data() -> list[str]:
    db = db_session()
    ade_matched = CatAdeParticella(
        national_cadastral_reference="H501-001-00001",
        administrative_unit="H501",
        codice_catastale="H501",
        foglio="1",
        particella="10",
        label="Fg 1 Part 10",
        raw_payload_json={"source": "ade"},
    )
    ade_unmatched = CatAdeParticella(
        national_cadastral_reference="H501-001-00002",
        administrative_unit="H501",
        codice_catastale="H501",
        foglio="1",
        particella="11",
        label="Fg 1 Part 11",
        raw_payload_json={"source": "ade"},
    )
    cat_particella = CatParticella(
        national_code="H501",
        cod_comune_capacitas=501,
        codice_catastale="H501",
        nome_comune="Comune Test",
        foglio="1",
        particella="10",
        source_type="test",
    )
    capacitas_snapshot = CatCapacitasGridSnapshot(
        snapshot_year=2026,
        source_file="capacitas.xlsx",
        file_hash="riordino-block-test",
        rows_total=1,
        rows_imported=1,
        counters_json={},
        imported_at=datetime.now(timezone.utc),
    )
    db.add_all([ade_matched, ade_unmatched, cat_particella, capacitas_snapshot])
    db.flush()
    db.add(
        CatCapacitasGridRow(
            snapshot_id=capacitas_snapshot.id,
            row_number=1,
            source_codice_catastale="H501",
            source_comune_label="Comune Test",
            foglio="1",
            particella="10",
            intestatario="Mario Rossi",
            codice_fiscale="RSSMRA80A01H501U",
            classification="ok",
            raw_payload_json={"source": "capacitas"},
        )
    )
    db.commit()
    ids = [str(ade_matched.id), str(ade_unmatched.id)]
    db.close()
    return ids


def find_step(detail: dict, code: str) -> tuple[dict, dict]:
    for phase in detail["phases"]:
        for step in phase["steps"]:
            if step["code"] == code:
                return phase, step
    raise AssertionError(f"Step {code} not found")


def mark_required_steps_done(practice_id: str, phase_code: str) -> None:
    practice_uuid = UUID(practice_id)
    db = db_session()
    phase = db.scalar(select(RiordinoPhase).where(RiordinoPhase.practice_id == practice_uuid, RiordinoPhase.phase_code == phase_code))
    steps = list(db.scalars(select(RiordinoStep).where(RiordinoStep.phase_id == phase.id)))
    for step in steps:
        if step.is_required:
            step.status = "done"
    if phase_code == "phase_1":
        practice = db.get(RiordinoPractice, practice_uuid)
        practice.status = "open"
    db.commit()
    db.close()


def upload_step_document(practice_id: str, phase_id: str, step_id: str, filename: str | None = None) -> dict:
    response = client.post(
        f"/api/riordino/practices/{practice_id}/documents",
        headers=auth_headers(),
        data={"document_type": "decreto", "phase_id": phase_id, "step_id": step_id},
        files={"file": (filename or f"{step_id}.pdf", b"%PDF-1.4 integration test", "application/pdf")},
    )
    assert response.status_code == 200, response.text
    return response.json()


def advance_step_by_code(practice_id: str, code: str, *, outcome_code: str | None = None, outcome_notes: str | None = None) -> dict:
    detail = get_detail(practice_id)
    phase, step = find_step(detail, code)
    if step["requires_document"]:
        upload_step_document(practice_id, phase["id"], step["id"], f"{code}.pdf")
    payload: dict[str, str] = {}
    if outcome_code is not None:
        payload["outcome_code"] = outcome_code
    if outcome_notes is not None:
        payload["outcome_notes"] = outcome_notes
    response = client.post(
        f"/api/riordino/practices/{practice_id}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json=payload,
    )
    assert response.status_code == 200, response.text
    return response.json()


def complete_phase_by_code(practice_id: str, phase_code: str) -> dict:
    detail = get_detail(practice_id)
    phase = next(item for item in detail["phases"] if item["phase_code"] == phase_code)
    response = client.post(
        f"/api/riordino/practices/{practice_id}/phases/{phase['id']}/complete",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_block_snapshots_ade_and_limits_dashboard_visibility_to_assignments():
    ade_ids = seed_block_source_data()
    response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco pilota AdE",
            "description": "Confronto AdE vs Capacitas",
            "municipality": "Comune Test",
            "selection_type": "parcel_list",
            "coordinator_user_id": 2,
            "operator_user_ids": [3],
            "ade_particella_ids": ade_ids,
        },
    )
    assert response.status_code == 201, response.text
    block = response.json()
    assert block["code"].startswith("RIOB-")
    assert block["parcel_count"] == 2
    assert block["mismatch_count"] == 1

    detail_response = client.get(f"/api/riordino/blocks/{block['id']}", headers=auth_headers())
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert {assignment["assignment_role"] for assignment in detail["assignments"]} == {"coordinator", "operator"}
    assert {assignment["user_id"] for assignment in detail["assignments"]} == {2, 3}

    snapshots_by_particella = {item["particella"]: item for item in detail["parcel_snapshots"]}
    assert snapshots_by_particella["10"]["cat_particella_match_status"] == "matched"
    assert snapshots_by_particella["10"]["capacitas_payload_json"]["match_status"] == "matched"
    assert snapshots_by_particella["10"]["sister_visura_status"] == "not_requested"
    assert snapshots_by_particella["11"]["cat_particella_match_status"] == "unmatched"
    assert {event["event_type"] for event in detail["events"]} == {"block_created"}

    operator_response = client.get("/api/riordino/blocks", headers=auth_headers_for("operator"))
    assert operator_response.status_code == 200, operator_response.text
    operator_payload = operator_response.json()
    assert operator_payload["total"] == 1
    assert operator_payload["items"][0]["id"] == block["id"]


def test_block_update_delete_dashboard_counts_and_invalid_status():
    seed_block_source_data()
    create_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco comune",
            "municipality": "Comune Test",
            "selection_type": "municipality",
            "codice_catastale": "H501",
            "coordinator_user_id": 2,
            "operator_user_ids": [2, 3],
        },
    )
    assert create_response.status_code == 201, create_response.text
    block = create_response.json()

    dashboard_response = client.get("/api/riordino/dashboard", headers=auth_headers())
    assert dashboard_response.status_code == 200, dashboard_response.text
    assert dashboard_response.json()["blocks_by_status"]["draft"] == 1

    invalid_response = client.patch(
        f"/api/riordino/blocks/{block['id']}",
        headers=auth_headers(),
        json={"status": "bad_status"},
    )
    assert invalid_response.status_code == 422

    update_response = client.patch(
        f"/api/riordino/blocks/{block['id']}",
        headers=auth_headers(),
        json={"title": "Blocco comune aggiornato", "status": "open", "operator_user_ids": [2, 3]},
    )
    assert update_response.status_code == 200, update_response.text
    assert update_response.json()["title"] == "Blocco comune aggiornato"
    assert update_response.json()["status"] == "open"

    detail_response = client.get(f"/api/riordino/blocks/{block['id']}", headers=auth_headers())
    assert detail_response.status_code == 200, detail_response.text
    detail = detail_response.json()
    assert {assignment["assignment_role"] for assignment in detail["assignments"]} == {"coordinator", "operator"}
    assert "block_updated" in {event["event_type"] for event in detail["events"]}

    delete_response = client.delete(f"/api/riordino/blocks/{block['id']}", headers=auth_headers())
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["deleted_at"] is not None

    list_response = client.get("/api/riordino/blocks", headers=auth_headers())
    assert list_response.status_code == 200, list_response.text
    assert list_response.json()["total"] == 0


def test_block_parcel_refs_empty_selection_and_unassigned_access_rules():
    seed_block_source_data()
    ref_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco da lista catastale",
            "selection_type": "parcel_list",
            "coordinator_user_id": 2,
            "parcel_refs": [{"codice_catastale": "H501", "foglio": "1", "particella": "10"}],
        },
    )
    assert ref_response.status_code == 201, ref_response.text
    block = ref_response.json()
    assert block["parcel_count"] == 1

    operator_detail_response = client.get(f"/api/riordino/blocks/{block['id']}", headers=auth_headers_for("operator"))
    assert operator_detail_response.status_code == 403

    operator_list_response = client.get("/api/riordino/blocks", headers=auth_headers_for("operator"))
    assert operator_list_response.status_code == 200, operator_list_response.text
    assert operator_list_response.json()["total"] == 0

    empty_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco vuoto",
            "selection_type": "parcel_list",
            "coordinator_user_id": 2,
            "ade_particella_ids": [str(uuid4())],
        },
    )
    assert empty_response.status_code == 422


def test_block_selection_validation_and_service_defensive_branches():
    for payload in (
        {"title": "No comune", "selection_type": "municipality", "coordinator_user_id": 2},
        {"title": "No lotto", "selection_type": "lot", "coordinator_user_id": 2, "codice_catastale": "H501"},
        {"title": "No particelle", "selection_type": "parcel_list", "coordinator_user_id": 2},
        {"title": "No gis", "selection_type": "gis_selection", "coordinator_user_id": 2},
    ):
        with pytest.raises(ValueError):
            BlockCreate.model_validate(payload)

    db = db_session()
    with pytest.raises(HTTPException) as municipality_error:
        _ade_query_for_selection(db, {"selection_type": "municipality"})
    assert municipality_error.value.status_code == 422
    with pytest.raises(HTTPException) as lot_error:
        _ade_query_for_selection(db, {"selection_type": "lot", "codice_catastale": "H501"})
    assert lot_error.value.status_code == 422
    with pytest.raises(HTTPException) as ref_error:
        _ade_query_for_selection(
            db,
            {
                "selection_type": "parcel_list",
                "parcel_refs": [{"foglio": "1", "particella": "10"}],
            },
        )
    assert ref_error.value.status_code == 422
    db.close()


def test_block_lot_gis_admin_filters_ambiguous_and_missing_keys():
    db = db_session()
    ade_lot = CatAdeParticella(
        national_cadastral_reference="H501-002-00001",
        administrative_unit="H501",
        foglio="2",
        particella="20",
        raw_payload_json={"source": "ade"},
    )
    ade_no_keys = CatAdeParticella(
        national_cadastral_reference="H501-003-00001",
        administrative_unit="H501",
        raw_payload_json={"source": "ade"},
    )
    db.add_all(
        [
            ade_lot,
            ade_no_keys,
            CatParticella(cod_comune_capacitas=501, codice_catastale="H501", foglio="2", particella="20"),
            CatParticella(cod_comune_capacitas=501, codice_catastale="H501", foglio="2", particella="20"),
        ]
    )
    db.commit()
    lot_id = str(ade_lot.id)
    no_keys_id = str(ade_no_keys.id)
    db.close()

    lot_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco lotto",
            "selection_type": "lot",
            "administrative_unit": "H501",
            "foglio": "2",
            "coordinator_user_id": 2,
        },
    )
    assert lot_response.status_code == 201, lot_response.text
    lot_block = lot_response.json()
    assert lot_block["code"].startswith("RIOB-")

    gis_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco GIS",
            "selection_type": "gis_selection",
            "coordinator_user_id": 2,
            "ade_particella_ids": [lot_id, no_keys_id],
        },
    )
    assert gis_response.status_code == 201, gis_response.text
    gis_block = gis_response.json()
    assert gis_block["code"] > lot_block["code"]

    detail_response = client.get(f"/api/riordino/blocks/{gis_block['id']}", headers=auth_headers())
    assert detail_response.status_code == 200, detail_response.text
    snapshots = {item["national_cadastral_reference"]: item for item in detail_response.json()["parcel_snapshots"]}
    assert snapshots["H501-002-00001"]["cat_particella_match_status"] == "ambiguous"
    assert snapshots["H501-003-00001"]["cat_particella_match_reason"] == "AdE parcel without foglio/particella"
    assert snapshots["H501-003-00001"]["capacitas_payload_json"]["reason"] == "AdE parcel without foglio/particella"

    filtered_response = client.get("/api/riordino/blocks?status=draft&coordinator=2", headers=auth_headers())
    assert filtered_response.status_code == 200, filtered_response.text
    assert filtered_response.json()["total"] == 2

    missing_response = client.get(f"/api/riordino/blocks/{uuid4()}", headers=auth_headers())
    assert missing_response.status_code == 404


def test_block_wizard_review_and_sister_visura_flow():
    ade_ids = seed_block_source_data()
    create_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco wizard",
            "selection_type": "parcel_list",
            "coordinator_user_id": 2,
            "operator_user_ids": [3],
            "ade_particella_ids": ade_ids,
        },
    )
    assert create_response.status_code == 201, create_response.text
    block = create_response.json()

    wizard_response = client.get(f"/api/riordino/blocks/{block['id']}/wizard", headers=auth_headers_for("operator"))
    assert wizard_response.status_code == 200, wizard_response.text
    wizard = wizard_response.json()
    assert wizard["block_code"] == block["code"]
    assert len(wizard["tasks"]) == 5

    detail_response = client.get(f"/api/riordino/blocks/{block['id']}", headers=auth_headers())
    assert detail_response.status_code == 200, detail_response.text
    snapshots = {item["particella"]: item for item in detail_response.json()["parcel_snapshots"]}
    matched_snapshot = snapshots["10"]
    unmatched_snapshot = snapshots["11"]

    review_response = client.patch(
        f"/api/riordino/blocks/{block['id']}/parcels/{matched_snapshot['id']}/review",
        headers=auth_headers_for("operator"),
        json={"status": "aligned", "notes": "Dati allineati"},
    )
    assert review_response.status_code == 200, review_response.text
    assert review_response.json()["operator_review_status"] == "aligned"
    assert review_response.json()["reviewed_by"] == 3

    request_response = client.post(
        f"/api/riordino/blocks/{block['id']}/parcels/{matched_snapshot['id']}/sister/request",
        headers=auth_headers_for("operator"),
        json={"enqueue": False, "request_id": "SIS-001", "notes": "Richiesta sintetica"},
    )
    assert request_response.status_code == 200, request_response.text
    assert request_response.json()["sister_visura_status"] == "requested"
    assert request_response.json()["sister_visura_requested_by"] == 3
    assert request_response.json()["sister_visura_request_id"] == "SIS-001"

    enqueue_response = client.post(
        f"/api/riordino/blocks/{block['id']}/parcels/{unmatched_snapshot['id']}/sister/request",
        headers=auth_headers_for("operator"),
        json={"notes": "Richiesta runtime SISTER"},
    )
    assert enqueue_response.status_code == 200, enqueue_response.text
    assert ":" in enqueue_response.json()["sister_visura_request_id"]
    db = db_session()
    assert db.query(ElaborazioneBatch).filter(ElaborazioneBatch.user_id == 3).count() == 1
    assert db.query(ElaborazioneRichiesta).filter(ElaborazioneRichiesta.user_id == 3).count() == 1
    db.close()

    requested_wizard_response = client.get(f"/api/riordino/blocks/{block['id']}/wizard", headers=auth_headers())
    assert requested_wizard_response.status_code == 200, requested_wizard_response.text
    requested_tasks = {item["code"]: item for item in requested_wizard_response.json()["tasks"]}
    assert requested_tasks[f"sister:{matched_snapshot['id']}"]["status"] == "in_progress"

    complete_validation_response = client.post(
        f"/api/riordino/blocks/{block['id']}/parcels/{matched_snapshot['id']}/sister/complete",
        headers=auth_headers_for("operator"),
        json={"status": "downloaded"},
    )
    assert complete_validation_response.status_code == 422

    failed_validation_response = client.post(
        f"/api/riordino/blocks/{block['id']}/parcels/{matched_snapshot['id']}/sister/complete",
        headers=auth_headers_for("operator"),
        json={"status": "failed"},
    )
    assert failed_validation_response.status_code == 422

    db = db_session()
    admin_user = db.get(ApplicationUser, 1)
    with pytest.raises(HTTPException):
        review_block_parcel(db, UUID(block["id"]), UUID(matched_snapshot["id"]), {"status": "bad"}, admin_user)
    with pytest.raises(HTTPException):
        complete_sister_visura(db, UUID(block["id"]), UUID(matched_snapshot["id"]), {"status": "bad"}, admin_user)
    with pytest.raises(HTTPException):
        complete_sister_visura(db, UUID(block["id"]), UUID(matched_snapshot["id"]), {"status": "downloaded"}, admin_user)
    with pytest.raises(HTTPException):
        complete_sister_visura(db, UUID(block["id"]), UUID(matched_snapshot["id"]), {"status": "failed"}, admin_user)
    db.close()

    complete_response = client.post(
        f"/api/riordino/blocks/{block['id']}/parcels/{matched_snapshot['id']}/sister/complete",
        headers=auth_headers_for("operator"),
        json={"status": "downloaded", "document_ref": "nas://visure/H501-1-10.pdf"},
    )
    assert complete_response.status_code == 200, complete_response.text
    assert complete_response.json()["sister_visura_status"] == "downloaded"
    assert complete_response.json()["sister_visura_document_ref"] == "nas://visure/H501-1-10.pdf"

    mismatch_review_response = client.patch(
        f"/api/riordino/blocks/{block['id']}/parcels/{unmatched_snapshot['id']}/review",
        headers=auth_headers_for("operator"),
        json={"status": "mismatch", "notes": "Capacitas non aggiornato"},
    )
    assert mismatch_review_response.status_code == 200, mismatch_review_response.text

    failed_response = client.post(
        f"/api/riordino/blocks/{block['id']}/parcels/{unmatched_snapshot['id']}/sister/complete",
        headers=auth_headers_for("operator"),
        json={"status": "failed", "error_message": "SISTER timeout"},
    )
    assert failed_response.status_code == 200, failed_response.text
    assert failed_response.json()["sister_visura_status"] == "failed"

    refreshed_wizard_response = client.get(f"/api/riordino/blocks/{block['id']}/wizard", headers=auth_headers())
    assert refreshed_wizard_response.status_code == 200, refreshed_wizard_response.text
    tasks_by_code = {item["code"]: item for item in refreshed_wizard_response.json()["tasks"]}
    assert tasks_by_code[f"compare:{matched_snapshot['id']}"]["status"] == "done"
    assert tasks_by_code[f"sister:{matched_snapshot['id']}"]["status"] == "done"
    assert tasks_by_code[f"compare:{unmatched_snapshot['id']}"]["status"] == "blocked"
    assert tasks_by_code[f"sister:{unmatched_snapshot['id']}"]["status"] == "blocked"
    assert tasks_by_code[f"resolve-mismatch:{unmatched_snapshot['id']}"]["assignee_hint"] == "coordinator"

    final_detail_response = client.get(f"/api/riordino/blocks/{block['id']}", headers=auth_headers())
    assert final_detail_response.status_code == 200, final_detail_response.text
    event_types = {event["event_type"] for event in final_detail_response.json()["events"]}
    assert "block_parcel_reviewed" in event_types
    assert "block_sister_visura_requested" in event_types
    assert "block_sister_visura_completed" in event_types

    coordinator_summary_response = client.get(
        f"/api/riordino/blocks/{block['id']}/coordinator-summary",
        headers=auth_headers_for("coordinator"),
    )
    assert coordinator_summary_response.status_code == 200, coordinator_summary_response.text
    coordinator_summary = coordinator_summary_response.json()
    assert coordinator_summary["review_status_counts"]["aligned"] == 1
    assert coordinator_summary["review_status_counts"]["mismatch"] == 1
    assert coordinator_summary["sister_status_counts"]["downloaded"] == 1
    assert coordinator_summary["sister_status_counts"]["failed"] == 1
    assert coordinator_summary["task_status_counts"]["done"] >= 2
    operator_summary = next(item for item in coordinator_summary["operators"] if item["user_id"] == 3)
    assert operator_summary["reviewed_count"] == 2
    assert operator_summary["sister_requested_count"] == 2
    assert operator_summary["sister_completed_count"] == 2
    assert operator_summary["last_activity_at"] is not None
    assert "block_sister_visura_completed" in {event["event_type"] for event in coordinator_summary["recent_events"]}

    admin_summary_response = client.get(f"/api/riordino/blocks/{block['id']}/coordinator-summary", headers=auth_headers())
    assert admin_summary_response.status_code == 200

    operator_summary_response = client.get(
        f"/api/riordino/blocks/{block['id']}/coordinator-summary",
        headers=auth_headers_for("operator"),
    )
    assert operator_summary_response.status_code == 403


def test_block_sister_request_requires_cadastral_keys():
    db = db_session()
    ade_no_keys = CatAdeParticella(
        national_cadastral_reference="H501-004-00001",
        administrative_unit="H501",
        raw_payload_json={"source": "ade"},
    )
    db.add(ade_no_keys)
    db.commit()
    ade_id = str(ade_no_keys.id)
    db.close()

    create_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco senza chiavi",
            "selection_type": "gis_selection",
            "coordinator_user_id": 2,
            "operator_user_ids": [3],
            "ade_particella_ids": [ade_id],
        },
    )
    assert create_response.status_code == 201, create_response.text
    block = create_response.json()

    detail_response = client.get(f"/api/riordino/blocks/{block['id']}", headers=auth_headers())
    assert detail_response.status_code == 200, detail_response.text
    snapshot_id = detail_response.json()["parcel_snapshots"][0]["id"]

    request_response = client.post(
        f"/api/riordino/blocks/{block['id']}/parcels/{snapshot_id}/sister/request",
        headers=auth_headers_for("operator"),
        json={},
    )
    assert request_response.status_code == 422

    missing_snapshot_response = client.patch(
        f"/api/riordino/blocks/{block['id']}/parcels/{uuid4()}/review",
        headers=auth_headers_for("operator"),
        json={"status": "aligned"},
    )
    assert missing_snapshot_response.status_code == 404


def test_block_sister_runtime_enqueue_error_branches():
    db = db_session()
    ade_missing_code = CatAdeParticella(
        national_cadastral_reference="NO-CODE-001",
        foglio="5",
        particella="50",
        raw_payload_json={"source": "ade"},
    )
    ade_unknown_comune = CatAdeParticella(
        national_cadastral_reference="UNKNOWN-COMUNE-001",
        codice_catastale="Z999",
        foglio="6",
        particella="60",
        raw_payload_json={"source": "ade"},
    )
    ade_known_comune = CatAdeParticella(
        national_cadastral_reference="KNOWN-COMUNE-001",
        codice_catastale="H501",
        foglio="7",
        particella="70",
        raw_payload_json={"source": "ade"},
    )
    db.add_all([ade_missing_code, ade_unknown_comune, ade_known_comune])
    db.commit()
    missing_code_id = str(ade_missing_code.id)
    unknown_comune_id = str(ade_unknown_comune.id)
    known_comune_id = str(ade_known_comune.id)
    db.close()

    missing_code_block_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco senza codice",
            "selection_type": "gis_selection",
            "coordinator_user_id": 2,
            "operator_user_ids": [3],
            "ade_particella_ids": [missing_code_id],
        },
    )
    assert missing_code_block_response.status_code == 201, missing_code_block_response.text
    missing_code_block = missing_code_block_response.json()
    missing_code_detail = client.get(f"/api/riordino/blocks/{missing_code_block['id']}", headers=auth_headers()).json()
    missing_code_snapshot_id = missing_code_detail["parcel_snapshots"][0]["id"]
    missing_code_request = client.post(
        f"/api/riordino/blocks/{missing_code_block['id']}/parcels/{missing_code_snapshot_id}/sister/request",
        headers=auth_headers_for("operator"),
        json={},
    )
    assert missing_code_request.status_code == 422

    unknown_block_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco comune non censito",
            "selection_type": "gis_selection",
            "coordinator_user_id": 2,
            "operator_user_ids": [3],
            "ade_particella_ids": [unknown_comune_id],
        },
    )
    assert unknown_block_response.status_code == 201, unknown_block_response.text
    unknown_block = unknown_block_response.json()
    unknown_detail = client.get(f"/api/riordino/blocks/{unknown_block['id']}", headers=auth_headers()).json()
    unknown_snapshot_id = unknown_detail["parcel_snapshots"][0]["id"]
    unknown_request = client.post(
        f"/api/riordino/blocks/{unknown_block['id']}/parcels/{unknown_snapshot_id}/sister/request",
        headers=auth_headers_for("operator"),
        json={},
    )
    assert unknown_request.status_code == 422
    assert "Comune non valido" in str(unknown_request.json()["detail"])

    known_block_response = client.post(
        "/api/riordino/blocks",
        headers=auth_headers(),
        json={
            "title": "Blocco senza credenziali admin",
            "selection_type": "gis_selection",
            "coordinator_user_id": 2,
            "ade_particella_ids": [known_comune_id],
        },
    )
    assert known_block_response.status_code == 201, known_block_response.text
    known_block = known_block_response.json()
    known_detail = client.get(f"/api/riordino/blocks/{known_block['id']}", headers=auth_headers()).json()
    known_snapshot_id = known_detail["parcel_snapshots"][0]["id"]
    no_credentials_request = client.post(
        f"/api/riordino/blocks/{known_block['id']}/parcels/{known_snapshot_id}/sister/request",
        headers=auth_headers(),
        json={"enqueue": True},
    )
    assert no_credentials_request.status_code == 409


def start_phase_by_code(practice_id: str, phase_code: str) -> dict:
    detail = get_detail(practice_id)
    phase = next(item for item in detail["phases"] if item["phase_code"] == phase_code)
    response = client.post(
        f"/api/riordino/practices/{practice_id}/phases/{phase['id']}/start",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_create_practice_generates_phases_and_steps():
    practice = create_practice()
    detail = get_detail(practice["id"])
    assert len(detail["phases"]) == 2
    assert detail["current_phase"] == "phase_1"


def test_create_practice_generates_correct_step_count():
    practice = create_practice()
    detail = get_detail(practice["id"])
    assert sum(len(phase["steps"]) for phase in detail["phases"]) == 25


def test_delete_practice_only_draft():
    practice = create_practice()
    detail = get_detail(practice["id"])
    _, step = find_step(detail, "F1_STUDIO_PIANO")
    advance_response = client.post(
        f"/api/riordino/practices/{practice['id']}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json={},
    )
    assert advance_response.status_code == 200
    delete_response = client.delete(f"/api/riordino/practices/{practice['id']}", headers=auth_headers())
    assert delete_response.status_code == 403


def test_advance_step_ok():
    practice = create_practice()
    detail = get_detail(practice["id"])
    _, step = find_step(detail, "F1_STUDIO_PIANO")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "done"


def test_advance_decision_step_without_outcome_fails():
    practice = create_practice()
    detail = get_detail(practice["id"])
    _, step = find_step(detail, "F1_OSSERVAZIONI")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 422


def test_advance_step_with_blocking_issue_fails():
    practice = create_practice()
    detail = get_detail(practice["id"])
    phase, step = find_step(detail, "F1_STUDIO_PIANO")
    issue_response = client.post(
        f"/api/riordino/practices/{practice['id']}/issues",
        headers=auth_headers(),
        json={
            "phase_id": phase["id"],
            "step_id": step["id"],
            "type": "anomalia",
            "category": "technical",
            "severity": "blocking",
            "title": "Blocco",
        },
    )
    assert issue_response.status_code == 200
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 403


def test_advance_step_requires_document_fails_without_doc():
    practice = create_practice()
    detail = get_detail(practice["id"])
    _, step = find_step(detail, "F1_PUBBLICAZIONE")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 422


def test_complete_phase1_with_open_appeal_fails():
    practice = create_practice()
    mark_required_steps_done(practice["id"], "phase_1")
    appeal_response = client.post(
        f"/api/riordino/practices/{practice['id']}/appeals",
        headers=auth_headers(),
        json={"appellant_name": "Mario Rossi", "filed_at": "2026-04-01"},
    )
    assert appeal_response.status_code == 200
    detail = get_detail(practice["id"])
    phase1 = next(phase for phase in detail["phases"] if phase["phase_code"] == "phase_1")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/phases/{phase1['id']}/complete",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 403


def test_complete_phase1_ok():
    practice = create_practice()
    mark_required_steps_done(practice["id"], "phase_1")
    detail = get_detail(practice["id"])
    phase1 = next(phase for phase in detail["phases"] if phase["phase_code"] == "phase_1")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/phases/{phase1['id']}/complete",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "completed"


def test_start_phase2_without_phase1_complete_fails():
    practice = create_practice()
    detail = get_detail(practice["id"])
    phase2 = next(phase for phase in detail["phases"] if phase["phase_code"] == "phase_2")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/phases/{phase2['id']}/start",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 403


def _prepare_phase2(practice_id: str) -> dict:
    mark_required_steps_done(practice_id, "phase_1")
    detail = get_detail(practice_id)
    phase1 = next(phase for phase in detail["phases"] if phase["phase_code"] == "phase_1")
    complete_response = client.post(
        f"/api/riordino/practices/{practice_id}/phases/{phase1['id']}/complete",
        headers=auth_headers(),
        json={},
    )
    assert complete_response.status_code == 200
    return get_detail(practice_id)


def test_branching_conforme_skips_anomalia_steps():
    practice = create_practice()
    detail = _prepare_phase2(practice["id"])
    _, step = find_step(detail, "F2_VERIFICA")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json={"outcome_code": "conforme"},
    )
    assert response.status_code == 200
    detail = get_detail(practice["id"])
    for code in ("F2_FUSIONE", "F2_DOCTE", "F2_RIPRISTINO"):
        _, branch_step = find_step(detail, code)
        assert branch_step["status"] == "skipped"


def test_branching_non_conforme_keeps_anomalia_steps():
    practice = create_practice()
    detail = _prepare_phase2(practice["id"])
    _, step = find_step(detail, "F2_VERIFICA")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json={"outcome_code": "non_conforme"},
    )
    assert response.status_code == 200
    detail = get_detail(practice["id"])
    for code in ("F2_FUSIONE", "F2_DOCTE", "F2_RIPRISTINO"):
        _, branch_step = find_step(detail, code)
        assert branch_step["status"] == "todo"


def test_create_appeal():
    practice = create_practice()
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/appeals",
        headers=auth_headers(),
        json={"appellant_name": "Ricorrente", "filed_at": "2026-04-01"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "open"


def test_resolve_appeal():
    practice = create_practice()
    create_response = client.post(
        f"/api/riordino/practices/{practice['id']}/appeals",
        headers=auth_headers(),
        json={"appellant_name": "Ricorrente", "filed_at": "2026-04-01"},
    )
    appeal_id = create_response.json()["id"]
    resolve_response = client.post(
        f"/api/riordino/practices/{practice['id']}/appeals/{appeal_id}/resolve",
        headers=auth_headers(),
        json={"status": "resolved_accepted", "resolution_notes": "OK"},
    )
    assert resolve_response.status_code == 200
    assert resolve_response.json()["status"] == "resolved_accepted"


def test_upload_document():
    practice = create_practice()
    detail = get_detail(practice["id"])
    phase, step = find_step(detail, "F1_PUBBLICAZIONE")
    response = client.post(
        f"/api/riordino/practices/{practice['id']}/documents",
        headers=auth_headers(),
        data={"document_type": "atto_pubblicazione", "phase_id": phase["id"], "step_id": step["id"]},
        files={"file": ("atto.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert response.status_code == 200
    assert Path(response.json()["storage_path"]).exists()


def test_soft_delete_document():
    practice = create_practice()
    detail = get_detail(practice["id"])
    phase, step = find_step(detail, "F1_PUBBLICAZIONE")
    upload_response = client.post(
        f"/api/riordino/practices/{practice['id']}/documents",
        headers=auth_headers(),
        data={"document_type": "atto_pubblicazione", "phase_id": phase["id"], "step_id": step["id"]},
        files={"file": ("atto.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    document_id = upload_response.json()["id"]
    delete_response = client.delete(f"/api/riordino/practices/documents/{document_id}", headers=auth_headers())
    assert delete_response.status_code == 200
    assert delete_response.json()["deleted_at"] is not None


def test_optimistic_locking_conflict():
    practice = create_practice()
    response = client.patch(
        f"/api/riordino/practices/{practice['id']}",
        headers=auth_headers(),
        json={"title": "Nuovo titolo", "version": 99},
    )
    assert response.status_code == 409


def test_dashboard_counts():
    practice_1 = create_practice()
    practice_2 = create_practice()
    detail = get_detail(practice_1["id"])
    _, step = find_step(detail, "F1_STUDIO_PIANO")
    response = client.post(
        f"/api/riordino/practices/{practice_1['id']}/steps/{step['id']}/advance",
        headers=auth_headers(),
        json={},
    )
    assert response.status_code == 200
    dashboard = client.get("/api/riordino/dashboard", headers=auth_headers())
    assert dashboard.status_code == 200
    payload = dashboard.json()
    assert payload["practices_by_status"]["draft"] == 1
    assert payload["practices_by_status"]["open"] == 1


def test_create_and_import_parcels():
    db = db_session()
    db.add(
        CatParticella(
            cod_comune_capacitas=1,
            codice_catastale="A001",
            nome_comune="Comune Demo",
            foglio="10",
            particella="22",
            subalterno=None,
            source_type="test",
        )
    )
    db.commit()
    db.close()
    practice = create_practice()
    update_response = client.patch(
        f"/api/riordino/practices/{practice['id']}",
        headers=auth_headers(),
        json={
            "version": practice["version"],
            "title": practice["title"],
            "municipality": "Comune Demo",
            "grid_code": practice["grid_code"],
            "lot_code": practice["lot_code"],
            "owner_user_id": practice["owner_user_id"],
        },
    )
    assert update_response.status_code == 200
    create_response = client.post(
        f"/api/riordino/practices/{practice['id']}/parcels",
        headers=auth_headers(),
        json={"foglio": "10", "particella": "22", "source": "manual"},
    )
    assert create_response.status_code == 200
    csv_response = client.post(
        f"/api/riordino/practices/{practice['id']}/parcels/import-csv",
        headers=auth_headers(),
        files={"file": ("particelle.csv", b"foglio,particella,source\n11,33,csv_import\n", "text/csv")},
    )
    assert csv_response.status_code == 200
    list_response = client.get(f"/api/riordino/practices/{practice['id']}/parcels", headers=auth_headers())
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 2
    matched = next(item for item in payload if item["particella"] == "22")
    unmatched = next(item for item in payload if item["particella"] == "33")
    assert matched["cat_particella_match_status"] == "matched"
    assert matched["cat_particella_nome_comune"] == "Comune Demo"
    assert matched["cat_particella_has_geometry"] is False
    assert unmatched["cat_particella_match_status"] == "unmatched"


def test_create_and_delete_party_link():
    db = db_session()
    subject = db.scalar(select(AnagraficaSubject))
    db.close()
    practice = create_practice()
    create_response = client.post(
        f"/api/riordino/practices/{practice['id']}/parties",
        headers=auth_headers(),
        json={"subject_id": str(subject.id), "role": "proprietario"},
    )
    assert create_response.status_code == 200
    party_id = create_response.json()["id"]
    list_response = client.get(f"/api/riordino/practices/{practice['id']}/parties", headers=auth_headers())
    assert list_response.status_code == 200
    assert len(list_response.json()) == 1
    delete_response = client.delete(
        f"/api/riordino/practices/{practice['id']}/parties/{party_id}",
        headers=auth_headers(),
    )
    assert delete_response.status_code == 200


def test_config_document_type_crud():
    list_response = client.get("/api/riordino/config/document-types", headers=auth_headers())
    assert list_response.status_code == 200
    assert any(item["code"] == "decreto" for item in list_response.json())

    create_response = client.post(
        "/api/riordino/config/document-types",
        headers=auth_headers(),
        json={
            "code": "verbale",
            "label": "Verbale",
            "description": "Verbale commissione",
            "sort_order": 20,
            "is_active": True,
        },
    )
    assert create_response.status_code == 200, create_response.text
    created = create_response.json()

    patch_response = client.patch(
        f"/api/riordino/config/document-types/{created['id']}",
        headers=auth_headers(),
        json={"label": "Verbale aggiornato", "is_active": False},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["label"] == "Verbale aggiornato"
    assert patch_response.json()["is_active"] is False

    delete_response = client.delete(
        f"/api/riordino/config/document-types/{created['id']}",
        headers=auth_headers(),
    )
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["code"] == "verbale"


def test_config_issue_type_crud():
    list_response = client.get("/api/riordino/config/issue-types", headers=auth_headers())
    assert list_response.status_code == 200
    assert any(item["code"] == "anomalia_documentale" for item in list_response.json())

    create_response = client.post(
        "/api/riordino/config/issue-types",
        headers=auth_headers(),
        json={
            "code": "errore_gis",
            "label": "Errore GIS",
            "category": "gis",
            "default_severity": "high",
            "description": "Errore di sincronizzazione GIS",
            "sort_order": 30,
            "is_active": True,
        },
    )
    assert create_response.status_code == 200, create_response.text
    created = create_response.json()

    patch_response = client.patch(
        f"/api/riordino/config/issue-types/{created['id']}",
        headers=auth_headers(),
        json={"default_severity": "blocking", "label": "Errore GIS bloccante"},
    )
    assert patch_response.status_code == 200, patch_response.text
    assert patch_response.json()["default_severity"] == "blocking"
    assert patch_response.json()["label"] == "Errore GIS bloccante"

    delete_response = client.delete(
        f"/api/riordino/config/issue-types/{created['id']}",
        headers=auth_headers(),
    )
    assert delete_response.status_code == 200, delete_response.text
    assert delete_response.json()["code"] == "errore_gis"


def test_config_municipalities_returns_distinct_practice_values():
    create_practice()
    second_response = client.post(
        "/api/riordino/practices",
        headers=auth_headers(),
        json={
            "title": "Pratica test 2",
            "municipality": "Comune Secondo",
            "grid_code": "M2",
            "lot_code": "L2",
            "owner_user_id": 1,
        },
    )
    assert second_response.status_code == 201, second_response.text

    response = client.get("/api/riordino/config/municipalities", headers=auth_headers())
    assert response.status_code == 200, response.text
    assert response.json() == ["Comune Secondo", "Comune Test"]


def test_export_practice_summary_csv():
    practice = create_practice()
    response = client.get(f"/api/riordino/practices/{practice['id']}/export/summary", headers=auth_headers())
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("text/csv")
    content_disposition = response.headers.get("content-disposition", "")
    assert "summary.csv" in content_disposition
    body = response.content.decode("utf-8")
    assert "practice_code,practice_title,municipality" in body
    assert practice["code"] in body


def test_export_practice_dossier_zip():
    practice = create_practice()
    detail = get_detail(practice["id"])
    phase, step = find_step(detail, "F1_PUBBLICAZIONE")
    upload_response = client.post(
        f"/api/riordino/practices/{practice['id']}/documents",
        headers=auth_headers(),
        data={"document_type": "atto_pubblicazione", "phase_id": phase["id"], "step_id": step["id"]},
        files={"file": ("atto.pdf", b"%PDF-1.4 test", "application/pdf")},
    )
    assert upload_response.status_code == 200, upload_response.text
    appeal_response = client.post(
        f"/api/riordino/practices/{practice['id']}/appeals",
        headers=auth_headers(),
        json={"appellant_name": "Ricorrente export", "filed_at": "2026-04-01"},
    )
    assert appeal_response.status_code == 200, appeal_response.text
    appeal_upload_response = client.post(
        f"/api/riordino/practices/{practice['id']}/documents",
        headers=auth_headers(),
        data={"document_type": "ricorso", "appeal_id": appeal_response.json()["id"]},
        files={"file": ("ricorso.pdf", b"%PDF-1.4 appeal", "application/pdf")},
    )
    assert appeal_upload_response.status_code == 200, appeal_upload_response.text

    response = client.get(f"/api/riordino/practices/{practice['id']}/export/dossier", headers=auth_headers())
    assert response.status_code == 200, response.text
    assert response.headers["content-type"].startswith("application/zip")

    import io
    import zipfile

    archive = zipfile.ZipFile(io.BytesIO(response.content))
    names = archive.namelist()
    assert "manifest.json" in names
    assert "summary/practice-summary.csv" in names
    assert any(name.endswith("/atto.pdf") for name in names)
    assert any(name.endswith("/ricorso.pdf") and "documents/appeals/" in name for name in names)


def test_riordino_module_denied_without_enabled_module():
    db = db_session()
    admin = db.scalar(select(ApplicationUser).where(ApplicationUser.username == "admin"))
    admin.module_riordino = False
    db.commit()
    db.close()

    response = client.get("/api/riordino/dashboard", headers=auth_headers())
    assert response.status_code == 403
    assert response.json()["detail"] == "Module access denied"


def test_riordino_section_denied_when_role_permission_revoked():
    db = db_session()
    section = db.scalar(select(Section).where(Section.key == "riordino.dashboard"))
    permission = db.scalar(
        select(RoleSectionPermission).where(
            RoleSectionPermission.section_id == section.id,
            RoleSectionPermission.role == "admin",
        )
    )
    permission.is_granted = False
    db.commit()
    db.close()

    response = client.get("/api/riordino/dashboard", headers=auth_headers())
    assert response.status_code == 403
    assert response.json()["detail"] == "Section access denied"


def test_demo_seed_creates_idempotent_demo_practices():
    db = db_session()
    first_run = ensure_demo_practices(db, owner_user_id=1, created_by_user_id=1)
    second_run = ensure_demo_practices(db, owner_user_id=1, created_by_user_id=1)
    titles = list(db.scalars(select(RiordinoPractice.title).order_by(RiordinoPractice.title.asc())))
    db.close()

    assert first_run == {"created": 5, "skipped": 0, "total": 5}
    assert second_run == {"created": 0, "skipped": 5, "total": 5}
    assert titles == [
        "DEMO Riordino - Archiviata",
        "DEMO Riordino - Completata",
        "DEMO Riordino - Draft",
        "DEMO Riordino - Fase 1 in corso",
        "DEMO Riordino - Fase 2 pronta",
    ]


def test_integration_standard_flow_phase1_to_phase2_to_complete_practice():
    practice = create_practice()

    for code in (
        "F1_STUDIO_PIANO",
        "F1_INDAGINE",
        "F1_ELABORAZIONE",
        "F1_PUBBLICAZIONE",
        "F1_OSSERVAZIONI",
        "F1_RISOLUZIONE",
        "F1_TRASCRIZIONE",
        "F1_CONSERVATORIA",
        "F1_VOLTURA",
        "F1_CARICAMENTO",
        "F1_OUTPUT",
    ):
        kwargs = {"outcome_code": "nessun_ricorso"} if code == "F1_OSSERVAZIONI" else {}
        advance_step_by_code(practice["id"], code, **kwargs)

    phase_1 = complete_phase_by_code(practice["id"], "phase_1")
    assert phase_1["status"] == "completed"

    phase_2 = start_phase_by_code(practice["id"], "phase_2")
    assert phase_2["status"] == "in_progress"

    for code in (
        "F2_SCARICO_DATI",
        "F2_CSV",
        "F2_VERIFICA",
        "F2_ESTRATTO_MAPPA",
        "F2_PREGEO",
        "F2_MAPPALE_UNITO",
        "F2_ATTI_RT",
        "F2_AGG_GIS",
        "F2_DOCUMENTO_FINALE",
    ):
        kwargs = {"outcome_code": "conforme"} if code == "F2_VERIFICA" else {}
        advance_step_by_code(practice["id"], code, **kwargs)

    phase_2 = complete_phase_by_code(practice["id"], "phase_2")
    assert phase_2["status"] == "completed"

    response = client.post(
        f"/api/riordino/practices/{practice['id']}/complete",
        headers=auth_headers(),
    )
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "completed"


def test_integration_appeal_flow_blocks_then_unblocks_phase1_completion():
    practice = create_practice()

    for code in (
        "F1_STUDIO_PIANO",
        "F1_INDAGINE",
        "F1_ELABORAZIONE",
        "F1_PUBBLICAZIONE",
        "F1_OSSERVAZIONI",
        "F1_RISOLUZIONE",
        "F1_TRASCRIZIONE",
        "F1_CONSERVATORIA",
        "F1_VOLTURA",
        "F1_CARICAMENTO",
        "F1_OUTPUT",
    ):
        kwargs = {"outcome_code": "ricorsi_presenti"} if code == "F1_OSSERVAZIONI" else {}
        advance_step_by_code(practice["id"], code, **kwargs)

    appeal_response = client.post(
        f"/api/riordino/practices/{practice['id']}/appeals",
        headers=auth_headers(),
        json={"appellant_name": "Mario Rossi", "filed_at": "2026-04-01"},
    )
    assert appeal_response.status_code == 200, appeal_response.text

    detail = get_detail(practice["id"])
    phase_1 = next(item for item in detail["phases"] if item["phase_code"] == "phase_1")
    blocked_response = client.post(
        f"/api/riordino/practices/{practice['id']}/phases/{phase_1['id']}/complete",
        headers=auth_headers(),
        json={},
    )
    assert blocked_response.status_code == 403

    resolve_response = client.post(
        f"/api/riordino/practices/{practice['id']}/appeals/{appeal_response.json()['id']}/resolve",
        headers=auth_headers(),
        json={"status": "resolved_accepted", "resolution_notes": "Ricorso accolto"},
    )
    assert resolve_response.status_code == 200, resolve_response.text

    completed_response = client.post(
        f"/api/riordino/practices/{practice['id']}/phases/{phase_1['id']}/complete",
        headers=auth_headers(),
        json={},
    )
    assert completed_response.status_code == 200, completed_response.text
    assert completed_response.json()["status"] == "completed"


def test_integration_anomaly_flow_keeps_branch_steps_available():
    practice = create_practice()

    for code in (
        "F1_STUDIO_PIANO",
        "F1_INDAGINE",
        "F1_ELABORAZIONE",
        "F1_PUBBLICAZIONE",
        "F1_OSSERVAZIONI",
        "F1_RISOLUZIONE",
        "F1_TRASCRIZIONE",
        "F1_CONSERVATORIA",
        "F1_VOLTURA",
        "F1_CARICAMENTO",
        "F1_OUTPUT",
    ):
        kwargs = {"outcome_code": "nessun_ricorso"} if code == "F1_OSSERVAZIONI" else {}
        advance_step_by_code(practice["id"], code, **kwargs)

    complete_phase_by_code(practice["id"], "phase_1")
    start_phase_by_code(practice["id"], "phase_2")

    advance_step_by_code(practice["id"], "F2_SCARICO_DATI")
    advance_step_by_code(practice["id"], "F2_CSV")
    advance_step_by_code(practice["id"], "F2_VERIFICA", outcome_code="non_conforme")

    detail = get_detail(practice["id"])
    for code in ("F2_FUSIONE", "F2_DOCTE", "F2_RIPRISTINO"):
        _, branch_step = find_step(detail, code)
        assert branch_step["status"] == "todo"

    advance_step_by_code(practice["id"], "F2_FUSIONE")
    advance_step_by_code(practice["id"], "F2_DOCTE")
    advance_step_by_code(practice["id"], "F2_RIPRISTINO")

    detail = get_detail(practice["id"])
    for code in ("F2_FUSIONE", "F2_DOCTE", "F2_RIPRISTINO"):
        _, branch_step = find_step(detail, code)
        assert branch_step["status"] == "done"


def test_integration_audit_trail_contains_expected_events():
    practice = create_practice()

    detail = get_detail(practice["id"])
    phase, step = find_step(detail, "F1_PUBBLICAZIONE")
    upload_step_document(practice["id"], phase["id"], step["id"], "audit.pdf")

    advance_step_by_code(practice["id"], "F1_STUDIO_PIANO")
    advance_step_by_code(practice["id"], "F1_PUBBLICAZIONE")

    for code in (
        "F1_INDAGINE",
        "F1_ELABORAZIONE",
        "F1_OSSERVAZIONI",
        "F1_RISOLUZIONE",
        "F1_TRASCRIZIONE",
        "F1_CONSERVATORIA",
        "F1_VOLTURA",
        "F1_CARICAMENTO",
        "F1_OUTPUT",
    ):
        kwargs = {"outcome_code": "nessun_ricorso"} if code == "F1_OSSERVAZIONI" else {}
        advance_step_by_code(practice["id"], code, **kwargs)

    complete_phase_by_code(practice["id"], "phase_1")

    response = client.get(f"/api/riordino/practices/{practice['id']}/events", headers=auth_headers())
    assert response.status_code == 200, response.text

    event_types = {item["event_type"] for item in response.json()}
    assert "practice_created" in event_types
    assert "phase_started" in event_types
    assert "document_uploaded" in event_types
    assert "step_completed" in event_types
    assert "phase_completed" in event_types
