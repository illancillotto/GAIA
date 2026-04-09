from __future__ import annotations

from collections.abc import Generator
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser
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
    db.commit()
    db.refresh(subject)
    db.close()
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


def db_session() -> Session:
    return TestingSessionLocal()


def auth_headers() -> dict[str, str]:
    response = client.post("/auth/login", json={"username": "admin", "password": "secret123"})
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
    practice = create_practice()
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
    assert len(list_response.json()) == 2


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
