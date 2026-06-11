"""
Test API WikiRequest: POST /wiki/requests, GET /wiki/requests, PATCH /wiki/requests/{id}.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.config import settings
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.wiki.models import WikiRequest, WikiRequestArtifact, WikiRequestEvent, WikiToolAuditLog


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


def override_get_db() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


client = TestClient(app)


@pytest.fixture(autouse=True)
def setup_database() -> Generator[None, None, None]:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(engine)
    yield
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def _create_user(username: str = "user", role: str = "viewer") -> ApplicationUser:
    db = TestingSessionLocal()
    user = ApplicationUser(
        username=username,
        email=f"{username}@test.local",
        password_hash=hash_password("pass123"),
        role=role,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    db.close()
    return user


def _login(username: str, password: str = "pass123") -> str:
    resp = client.post("/auth/login", json={"username": username, "password": password})
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


# ── POST /wiki/requests ───────────────────────────────────────────────────────

def test_create_wiki_request_returns_201() -> None:
    _create_user("alice", "viewer")
    token = _login("alice")

    resp = client.post(
        "/wiki/requests",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_question": "Come si aggiunge un nuovo modulo?",
            "category": "question",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["user_question"] == "Come si aggiunge un nuovo modulo?"
    assert data["status"] == "new"
    assert data["priority"] == "medium"
    assert data["category"] == "question"
    assert data["created_by"] == "alice"
    assert data["request_type"] == "help_request"
    assert data["severity"] == "medium"


def test_create_wiki_request_saves_agent_response() -> None:
    _create_user("bob", "viewer")
    token = _login("bob")

    resp = client.post(
        "/wiki/requests",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_question": "Feature X?",
            "agent_response": "Non ancora implementata.",
            "category": "feature_request",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["agent_response"] == "Non ancora implementata."


def test_create_wiki_request_saves_support_context() -> None:
    _create_user("support_user", "viewer")
    token = _login("support_user")

    resp = client.post(
        "/wiki/requests",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "user_question": "Non riesco a usare la vista rete",
            "agent_response": "Il Wiki non ha trovato contesto sufficiente.",
            "category": "support_request",
            "request_type": "access_issue",
            "module_key": "rete",
            "page_path": "/network/devices",
            "source_channel": "support_page",
            "severity": "high",
            "impact_scope": "team",
            "conversation_id": str(uuid.uuid4()),
            "context_article": "domain-docs/network/docs/PRD_network.md",
            "context_entity_key": "device:192.168.1.10",
            "desired_outcome": "Capire come sbloccare la funzione",
            "observed_behavior": "La pagina mostra errore",
            "expected_behavior": "La vista dovrebbe caricarsi",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["category"] == "support_request"
    assert data["request_type"] == "access_issue"
    assert data["module_key"] == "rete"
    assert data["page_path"] == "/network/devices"
    assert data["source_channel"] == "support_page"
    assert data["severity"] == "high"
    assert data["impact_scope"] == "team"
    assert data["context_entity_key"] == "device:192.168.1.10"
    assert data["desired_outcome"] == "Capire come sbloccare la funzione"


def test_create_wiki_request_with_artifacts_persists_snapshot_files(tmp_path: Path) -> None:
    _create_user("artifact_user", "viewer")
    token = _login("artifact_user")

    previous_path = settings.wiki_request_artifacts_path
    settings.wiki_request_artifacts_path = str(tmp_path)
    try:
        resp = client.post(
            "/wiki/requests/with-artifacts",
            headers={"Authorization": f"Bearer {token}"},
            data={
                "payload_json": json.dumps(
                    {
                        "user_question": "Mi serve una nuova vista per il caso aperto",
                        "category": "feature_request",
                        "request_type": "feature_request",
                        "module_key": "operazioni",
                        "page_path": "/operazioni/casi/123",
                        "source_channel": "support_page",
                    }
                ),
                "screenshot_meta_json": json.dumps({"capture_method": "svg_foreign_object", "width": 1440}),
                "ui_snapshot_json": json.dumps({"heading": "Caso 123", "location": {"pathname": "/operazioni/casi/123"}}),
            },
            files={"screenshot": ("case.jpg", b"fake-image-bytes", "image/jpeg")},
        )
    finally:
        settings.wiki_request_artifacts_path = previous_path

    assert resp.status_code == 201, resp.text
    request_id = uuid.UUID(resp.json()["id"])

    db = TestingSessionLocal()
    artifacts = db.query(WikiRequestArtifact).filter_by(request_id=request_id).all()
    db.close()

    assert len(artifacts) == 3
    screenshot_artifact = next(item for item in artifacts if item.artifact_type == "screenshot")
    assert screenshot_artifact.mime_type == "image/jpeg"
    assert screenshot_artifact.storage_path is not None
    assert Path(screenshot_artifact.storage_path).exists()


def test_create_wiki_request_unauthenticated_returns_401() -> None:
    resp = client.post("/wiki/requests", json={"user_question": "Test", "category": "question"})
    assert resp.status_code == 401


def test_create_wiki_request_empty_question_returns_422() -> None:
    _create_user("charlie", "viewer")
    token = _login("charlie")

    resp = client.post(
        "/wiki/requests",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_question": "", "category": "question"},
    )
    assert resp.status_code == 422


# ── GET /wiki/requests ────────────────────────────────────────────────────────

def test_admin_can_list_requests() -> None:
    _create_user("admin_user", "admin")
    _create_user("mario", "reviewer")
    token = _login("admin_user")

    # Crea una richiesta
    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=uuid.uuid4(),
        user_question="Domanda test",
        category="question",
        request_type="help_request",
        status="new",
        priority="high",
        severity="critical",
        created_by="someone",
        assigned_to="mario",
        module_key="wiki",
        source_channel="wiki_page",
    ))
    db.commit()
    db.close()

    resp = client.get("/wiki/requests", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["user_question"] == "Domanda test"
    assert data[0]["priority"] == "high"
    assert data[0]["severity"] == "critical"
    assert data[0]["assigned_to"] == "mario"
    assert data[0]["assigned_to_name"] == "mario"


def test_user_can_list_own_requests() -> None:
    _create_user("myself", "viewer")
    _create_user("other", "viewer")
    token = _login("myself")

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=uuid.uuid4(),
        user_question="La mia richiesta",
        category="support_request",
        request_type="help_request",
        status="new",
        priority="medium",
        severity="medium",
        created_by="myself",
    ))
    db.add(WikiRequest(
        id=uuid.uuid4(),
        user_question="Richiesta altrui",
        category="feature_request",
        request_type="feature_request",
        status="new",
        priority="medium",
        severity="medium",
        created_by="other",
    ))
    db.commit()
    db.close()

    resp = client.get("/wiki/requests/mine", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["created_by"] == "myself"
    assert data[0]["user_question"] == "La mia richiesta"


def test_user_can_get_my_requests_summary() -> None:
    _create_user("summary_owner", "viewer")
    token = _login("summary_owner")

    db = TestingSessionLocal()
    waiting = WikiRequest(
        id=uuid.uuid4(),
        user_question="Aspetto risposta admin",
        category="support_request",
        request_type="help_request",
        status="waiting_user",
        priority="medium",
        severity="medium",
        created_by="summary_owner",
    )
    resolved = WikiRequest(
        id=uuid.uuid4(),
        user_question="Caso risolto ma senza feedback",
        category="support_request",
        request_type="data_issue",
        status="resolved",
        priority="medium",
        severity="medium",
        created_by="summary_owner",
    )
    duplicate = WikiRequest(
        id=uuid.uuid4(),
        user_question="Caso duplicato",
        category="support_request",
        request_type="bug_report",
        status="duplicate",
        priority="medium",
        severity="medium",
        created_by="summary_owner",
    )
    db.add_all([waiting, resolved, duplicate])
    db.commit()
    persisted_duplicate = db.query(WikiRequest).filter(WikiRequest.id == duplicate.id).first()
    assert persisted_duplicate is not None
    persisted_duplicate.last_admin_update_at = persisted_duplicate.updated_at
    db.commit()
    db.close()

    resp = client.get("/wiki/requests/mine/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["total_requests"] == 3
    assert data["open_requests"] == 1
    assert data["waiting_user_requests"] == 1
    assert data["resolved_feedback_pending"] == 1
    assert data["unread_updates"] == 1


def test_super_admin_can_list_requests() -> None:
    _create_user("superadmin", "super_admin")
    token = _login("superadmin")
    resp = client.get("/wiki/requests", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


def test_admin_can_get_request_by_id() -> None:
    _create_user("admin_get_request", "admin")
    token = _login("admin_get_request")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Serve supporto wiki",
        category="support_request",
        request_type="help_request",
        status="new",
        priority="medium",
        severity="medium",
        created_by="alice",
    ))
    db.commit()
    db.close()

    resp = client.get(f"/wiki/requests/{req_id}", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json()["id"] == str(req_id)


def test_admin_can_list_duplicate_candidates() -> None:
    _create_user("admin_duplicates", "admin")
    token = _login("admin_duplicates")
    source_id = uuid.uuid4()
    duplicate_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=source_id,
        user_question="La pagina rete non si apre e mostra un errore 500",
        category="support_request",
        request_type="bug_report",
        status="new",
        priority="medium",
        severity="high",
        created_by="alice",
        module_key="rete",
        page_path="/network/devices",
        dedupe_key="bug_report|rete|network devices|unknown|pagina rete non si apre mostra errore 500",
    ))
    db.add(WikiRequest(
        id=duplicate_id,
        user_question="Errore 500 nella pagina rete dispositivi",
        category="bug_report",
        request_type="bug_report",
        status="triaged",
        priority="high",
        severity="high",
        created_by="mario",
        module_key="rete",
        page_path="/network/devices",
        dedupe_key="bug_report|rete|network devices|unknown|errore 500 nella pagina rete dispositivi",
    ))
    db.add(WikiRequest(
        id=uuid.uuid4(),
        user_question="Richiesta senza relazione",
        category="feature_request",
        request_type="feature_request",
        status="new",
        priority="medium",
        severity="medium",
        created_by="other",
        module_key="wiki",
    ))
    db.commit()
    db.close()

    resp = client.get(f"/wiki/requests/{source_id}/duplicates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(duplicate_id)
    assert data[0]["status"] == "triaged"
    assert data[0]["similarity_score"] >= 0.45


def test_admin_can_list_linked_duplicates_for_canonical_case() -> None:
    _create_user("admin_linked_duplicates", "admin")
    token = _login("admin_linked_duplicates")
    canonical_id = uuid.uuid4()
    duplicate_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=canonical_id,
        user_question="Caso canonico rete",
        category="bug_report",
        request_type="bug_report",
        status="investigating",
        priority="high",
        severity="high",
        created_by="alice",
        module_key="rete",
    ))
    db.add(WikiRequest(
        id=duplicate_id,
        user_question="Stesso errore rete",
        category="support_request",
        request_type="bug_report",
        status="duplicate",
        priority="medium",
        severity="high",
        created_by="mario",
        module_key="rete",
        canonical_request_id=canonical_id,
    ))
    db.commit()
    db.close()

    resp = client.get(f"/wiki/requests/{canonical_id}/linked-duplicates", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["id"] == str(duplicate_id)
    assert data[0]["match_reason"] == "collegata a questo caso canonico"


def test_admin_can_get_request_family() -> None:
    _create_user("admin_request_family", "admin")
    token = _login("admin_request_family")
    canonical_id = uuid.uuid4()
    duplicate_a_id = uuid.uuid4()
    duplicate_b_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(
        WikiRequest(
            id=canonical_id,
            user_question="Caso canonico wiki",
            category="bug_report",
            request_type="bug_report",
            status="investigating",
            priority="high",
            severity="high",
            created_by="alice",
            module_key="wiki",
        )
    )
    db.add(
        WikiRequest(
            id=duplicate_a_id,
            user_question="Errore simile widget wiki",
            category="support_request",
            request_type="bug_report",
            status="duplicate",
            priority="medium",
            severity="high",
            created_by="mario",
            canonical_request_id=canonical_id,
        )
    )
    db.add(
        WikiRequest(
            id=duplicate_b_id,
            user_question="Secondo caso simile widget wiki",
            category="support_request",
            request_type="bug_report",
            status="duplicate",
            priority="medium",
            severity="high",
            created_by="laura",
            canonical_request_id=canonical_id,
        )
    )
    db.commit()
    db.close()

    resp = client.get(f"/wiki/requests/{duplicate_a_id}/family", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["canonical_request"]["id"] == str(canonical_id)
    assert data["family_size"] == 3
    assert data["affected_users"] == 3
    assert len(data["linked_duplicates"]) == 2


def test_viewer_cannot_list_requests() -> None:
    _create_user("viewer_user", "viewer")
    token = _login("viewer_user")
    resp = client.get("/wiki/requests", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_reviewer_cannot_list_requests() -> None:
    _create_user("rev", "reviewer")
    token = _login("rev")
    resp = client.get("/wiki/requests", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403


def test_admin_can_list_request_assignees() -> None:
    _create_user("admin_assignees", "admin")
    _create_user("review_user", "reviewer")
    _create_user("inactive_user", "viewer")
    db = TestingSessionLocal()
    inactive = db.query(ApplicationUser).filter(ApplicationUser.username == "inactive_user").first()
    assert inactive is not None
    inactive.is_active = False
    db.commit()
    db.close()
    token = _login("admin_assignees")

    resp = client.get("/wiki/requests/assignees", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    usernames = {item["username"] for item in data}
    assert "admin_assignees" in usernames
    assert "review_user" in usernames
    assert "inactive_user" not in usernames


# ── PATCH /wiki/requests/{id} ─────────────────────────────────────────────────

def test_admin_can_update_request_status() -> None:
    _create_user("admin2", "admin")
    _create_user("operator1", "operator")
    token = _login("admin2")

    req_id = uuid.uuid4()
    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Feature richiesta",
        category="feature_request",
        request_type="feature_request",
        status="new",
        priority="medium",
        severity="medium",
    ))
    db.commit()
    db.close()

    resp = client.patch(
        f"/wiki/requests/{req_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "status": "planned",
            "priority": "urgent",
            "severity": "critical",
            "assigned_to": "operator1",
            "resolution_message": "La richiesta è stata presa in carico e pianificata.",
            "admin_notes": "Pianificata per Q3.",
            "external_ticket_key": "GAIA-123",
            "external_ticket_url": "https://tracker.example.test/browse/GAIA-123",
            "delivery_status": "in_progress",
            "delivery_notes": "Sviluppo avviato su branch feature/wiki-delivery-bridge.",
        },
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "planned"
    assert data["priority"] == "urgent"
    assert data["severity"] == "critical"
    assert data["assigned_to"] == "operator1"
    assert data["resolution_message"] == "La richiesta è stata presa in carico e pianificata."
    assert data["admin_notes"] == "Pianificata per Q3."
    assert data["external_ticket_key"] == "GAIA-123"
    assert data["external_ticket_url"] == "https://tracker.example.test/browse/GAIA-123"
    assert data["delivery_status"] == "in_progress"
    assert data["delivery_notes"] == "Sviluppo avviato su branch feature/wiki-delivery-bridge."
    assert data["has_unread_update"] is True


def test_update_request_rejects_duplicate_without_canonical_reference() -> None:
    _create_user("admin_duplicate_guard", "admin")
    token = _login("admin_duplicate_guard")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Segnalazione da deduplicare",
        category="support_request",
        request_type="bug_report",
        status="new",
        priority="medium",
        severity="medium",
    ))
    db.commit()
    db.close()

    resp = client.patch(
        f"/wiki/requests/{req_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "duplicate"},
    )
    assert resp.status_code == 422
    assert "caso canonico" in resp.text


def test_admin_can_mark_request_as_duplicate_of_canonical_case() -> None:
    _create_user("admin_mark_duplicate", "admin")
    token = _login("admin_mark_duplicate")
    req_id = uuid.uuid4()
    canonical_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Il widget wiki non si apre nella dashboard",
        category="support_request",
        request_type="bug_report",
        status="new",
        priority="medium",
        severity="high",
        created_by="alice",
        module_key="wiki",
        page_path="/dashboard",
    ))
    db.add(WikiRequest(
        id=canonical_id,
        user_question="Dashboard: widget wiki invisibile",
        category="bug_report",
        request_type="bug_report",
        status="investigating",
        priority="high",
        severity="high",
        created_by="mario",
        module_key="wiki",
        page_path="/dashboard",
    ))
    db.commit()
    db.close()

    resp = client.post(
        f"/wiki/requests/{req_id}/mark-duplicate",
        headers={"Authorization": f"Bearer {token}"},
        json={"canonical_request_id": str(canonical_id), "admin_notes": "Accorpata al caso principale."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "duplicate"
    assert data["canonical_request_id"] == str(canonical_id)
    assert data["canonical_request_question"] == "Dashboard: widget wiki invisibile"
    assert data["admin_notes"] == "Accorpata al caso principale."

    events_resp = client.get(f"/wiki/requests/{req_id}/events", headers={"Authorization": f"Bearer {token}"})
    assert events_resp.status_code == 200
    event_types = [item["event_type"] for item in events_resp.json()]
    assert "marked_duplicate" in event_types
    assert "status_changed" in event_types


def test_admin_can_unlink_duplicate_request() -> None:
    _create_user("admin_unlink_duplicate", "admin")
    token = _login("admin_unlink_duplicate")
    req_id = uuid.uuid4()
    canonical_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Caso duplicato da sganciare",
        category="support_request",
        request_type="bug_report",
        status="duplicate",
        priority="medium",
        severity="high",
        created_by="alice",
        canonical_request_id=canonical_id,
    ))
    db.add(WikiRequest(
        id=canonical_id,
        user_question="Caso canonico",
        category="bug_report",
        request_type="bug_report",
        status="investigating",
        priority="high",
        severity="high",
        created_by="mario",
    ))
    db.commit()
    db.close()

    resp = client.post(f"/wiki/requests/{req_id}/unlink-duplicate", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "triaged"
    assert data["canonical_request_id"] is None

    events_resp = client.get(f"/wiki/requests/{req_id}/events", headers={"Authorization": f"Bearer {token}"})
    assert events_resp.status_code == 200
    event_types = [item["event_type"] for item in events_resp.json()]
    assert "duplicate_unlinked" in event_types
    assert "status_changed" in event_types


def test_admin_can_promote_duplicate_to_new_canonical() -> None:
    _create_user("admin_make_canonical", "admin")
    token = _login("admin_make_canonical")
    canonical_id = uuid.uuid4()
    target_id = uuid.uuid4()
    sibling_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(
        WikiRequest(
            id=canonical_id,
            user_question="Caso canonico iniziale",
            category="bug_report",
            request_type="bug_report",
            status="investigating",
            priority="high",
            severity="high",
            created_by="alice",
            module_key="wiki",
        )
    )
    db.add(
        WikiRequest(
            id=target_id,
            user_question="Questo dovrebbe diventare il canonico",
            category="support_request",
            request_type="bug_report",
            status="duplicate",
            priority="medium",
            severity="high",
            created_by="mario",
            canonical_request_id=canonical_id,
        )
    )
    db.add(
        WikiRequest(
            id=sibling_id,
            user_question="Altro duplicato collegato",
            category="support_request",
            request_type="bug_report",
            status="duplicate",
            priority="medium",
            severity="high",
            created_by="laura",
            canonical_request_id=canonical_id,
        )
    )
    db.commit()
    db.close()

    resp = client.post(
        f"/wiki/requests/{target_id}/make-canonical",
        headers={"Authorization": f"Bearer {token}"},
        json={"admin_notes": "Promosso come riferimento corretto."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["canonical_request"]["id"] == str(target_id)
    assert data["canonical_request"]["status"] == "triaged"
    assert data["family_size"] == 3

    db = TestingSessionLocal()
    target = db.query(WikiRequest).filter(WikiRequest.id == target_id).first()
    old_canonical = db.query(WikiRequest).filter(WikiRequest.id == canonical_id).first()
    sibling = db.query(WikiRequest).filter(WikiRequest.id == sibling_id).first()
    assert target is not None and old_canonical is not None and sibling is not None
    assert target.canonical_request_id is None
    assert old_canonical.canonical_request_id == target_id
    assert old_canonical.status == "duplicate"
    assert sibling.canonical_request_id == target_id
    db.close()

    target_events = client.get(f"/wiki/requests/{target_id}/events", headers={"Authorization": f"Bearer {token}"}).json()
    old_canonical_events = client.get(f"/wiki/requests/{canonical_id}/events", headers={"Authorization": f"Bearer {token}"}).json()
    sibling_events = client.get(f"/wiki/requests/{sibling_id}/events", headers={"Authorization": f"Bearer {token}"}).json()
    assert "canonical_promoted" in [item["event_type"] for item in target_events]
    assert "canonical_demoted" in [item["event_type"] for item in old_canonical_events]
    assert "canonical_reassigned" in [item["event_type"] for item in sibling_events]


def test_user_can_mark_own_request_as_viewed() -> None:
    _create_user("viewer_mark_viewed", "viewer")
    token = _login("viewer_mark_viewed")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Mi serve aggiornamento",
        category="support_request",
        request_type="help_request",
        status="waiting_user",
        priority="medium",
        severity="medium",
        created_by="viewer_mark_viewed",
        last_admin_update_at=None,
    ))
    db.commit()
    req = db.query(WikiRequest).filter(WikiRequest.id == req_id).first()
    assert req is not None
    req.last_admin_update_at = req.updated_at
    db.commit()
    db.close()

    resp = client.post(f"/wiki/requests/{req_id}/mark-viewed", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user_last_viewed_at"] is not None
    assert data["has_unread_update"] is False


def test_user_can_submit_feedback_on_own_request() -> None:
    _create_user("viewer_feedback", "viewer")
    token = _login("viewer_feedback")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Caso da chiudere",
        category="support_request",
        request_type="help_request",
        status="resolved",
        priority="medium",
        severity="medium",
        created_by="viewer_feedback",
    ))
    db.commit()
    db.close()

    resp = client.patch(
        f"/wiki/requests/{req_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={"rating": "not_helpful", "notes": "Il problema si ripresenta."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["user_feedback_rating"] == "not_helpful"
    assert data["user_feedback_notes"] == "Il problema si ripresenta."
    assert data["user_feedback_submitted_at"] is not None

    admin = _create_user("admin_feedback_check", "admin")
    assert admin.username == "admin_feedback_check"
    admin_token = _login("admin_feedback_check")
    events_resp = client.get(f"/wiki/requests/{req_id}/events", headers={"Authorization": f"Bearer {admin_token}"})
    assert events_resp.status_code == 200
    assert "user_feedback_submitted" in [item["event_type"] for item in events_resp.json()]


def test_user_can_reopen_own_request() -> None:
    _create_user("viewer_reopen", "viewer")
    token = _login("viewer_reopen")
    req_id = uuid.uuid4()
    canonical_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Il problema persiste",
        category="support_request",
        request_type="bug_report",
        status="duplicate",
        priority="medium",
        severity="medium",
        created_by="viewer_reopen",
        canonical_request_id=canonical_id,
    ))
    db.commit()
    db.close()

    resp = client.post(
        f"/wiki/requests/{req_id}/reopen",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Il caso non corrisponde al mio problema reale."},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "investigating"
    assert data["canonical_request_id"] is None
    assert data["user_feedback_rating"] == "not_helpful"
    assert data["user_feedback_notes"] == "Il caso non corrisponde al mio problema reale."

    admin = _create_user("admin_reopen_check", "admin")
    assert admin.username == "admin_reopen_check"
    admin_token = _login("admin_reopen_check")
    events_resp = client.get(f"/wiki/requests/{req_id}/events", headers={"Authorization": f"Bearer {admin_token}"})
    assert events_resp.status_code == 200
    assert "reopened_by_user" in [item["event_type"] for item in events_resp.json()]


def test_update_request_rejects_unknown_assignee() -> None:
    _create_user("admin_unknown", "admin")
    token = _login("admin_unknown")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Feature richiesta",
        category="feature_request",
        request_type="feature_request",
        status="new",
        priority="medium",
        severity="medium",
    ))
    db.commit()
    db.close()

    resp = client.patch(
        f"/wiki/requests/{req_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"assigned_to": "missing.user"},
    )
    assert resp.status_code == 422


def test_update_request_not_found_returns_404() -> None:
    _create_user("admin3", "admin")
    token = _login("admin3")
    fake_id = uuid.uuid4()

    resp = client.patch(
        f"/wiki/requests/{fake_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "resolved"},
    )
    assert resp.status_code == 404


def test_viewer_cannot_update_request() -> None:
    _create_user("viewer2", "viewer")
    token = _login("viewer2")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(id=req_id, user_question="Q", category="question", request_type="help_request", status="new", severity="medium"))
    db.commit()
    db.close()

    resp = client.patch(
        f"/wiki/requests/{req_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "resolved"},
    )
    assert resp.status_code == 403


def test_unauthenticated_cannot_update_request() -> None:
    resp = client.patch(f"/wiki/requests/{uuid.uuid4()}", json={"status": "resolved"})
    assert resp.status_code == 401


def test_admin_can_list_request_events() -> None:
    _create_user("admin_events", "admin")
    token = _login("admin_events")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(
        WikiRequest(
            id=req_id,
            user_question="Serve aiuto sulla rete",
            category="support_request",
            request_type="help_request",
            status="triaged",
            priority="medium",
            severity="high",
        )
    )
    db.add(
        WikiRequestEvent(
            id=uuid.uuid4(),
            request_id=req_id,
            event_type="status_changed",
            actor_username="admin_events",
            from_status="new",
            to_status="triaged",
            payload_json='{"note":"triage iniziale"}',
        )
    )
    db.commit()
    db.close()

    resp = client.get(f"/wiki/requests/{req_id}/events", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) == 1
    assert data[0]["event_type"] == "status_changed"
    assert data[0]["from_status"] == "new"
    assert data[0]["to_status"] == "triaged"
    assert data[0]["payload"]["note"] == "triage iniziale"


def test_update_request_creates_timeline_events() -> None:
    _create_user("admin_timeline", "admin")
    _create_user("owner_wiki", "operator")
    token = _login("admin_timeline")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(
        WikiRequest(
            id=req_id,
            user_question="Segnalazione",
            category="bug_report",
            request_type="bug_report",
            status="new",
            priority="medium",
            severity="medium",
        )
    )
    db.commit()
    db.close()

    resp = client.patch(
        f"/wiki/requests/{req_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "status": "investigating",
            "priority": "high",
            "severity": "critical",
            "assigned_to": "owner_wiki",
            "admin_notes": "Aperta analisi tecnica.",
        },
    )
    assert resp.status_code == 200, resp.text

    timeline_resp = client.get(f"/wiki/requests/{req_id}/events", headers={"Authorization": f"Bearer {token}"})
    assert timeline_resp.status_code == 200, timeline_resp.text
    event_types = {item["event_type"] for item in timeline_resp.json()}
    assert "status_changed" in event_types
    assert "priority_changed" in event_types
    assert "severity_changed" in event_types
    assert "assignee_changed" in event_types
    assert "notes_updated" in event_types


def test_admin_can_read_support_analytics_summary_and_series() -> None:
    _create_user("supportadmin", "admin")
    token = _login("supportadmin")

    db = TestingSessionLocal()
    db.add_all(
        [
            WikiRequest(
                id=uuid.uuid4(),
                user_question="Mi serve una feature nuova",
                category="feature_request",
                request_type="feature_request",
                status="planned",
                priority="high",
                severity="medium",
                created_by="alice",
                module_key="wiki",
                source_channel="widget",
                page_path="/wiki",
                impact_scope="team",
            ),
            WikiRequest(
                id=uuid.uuid4(),
                user_question="La pagina rete va in errore",
                category="bug_report",
                request_type="bug_report",
                status="investigating",
                priority="urgent",
                severity="critical",
                created_by="bob",
                assigned_to="owner_wiki",
                module_key="rete",
                source_channel="support_page",
                page_path="/network/devices",
                impact_scope="office",
            ),
            WikiRequest(
                id=uuid.uuid4(),
                user_question="Non vedo i dati attesi",
                category="support_request",
                request_type="data_issue",
                status="resolved",
                priority="medium",
                severity="high",
                created_by="carol",
                module_key="catasto",
                source_channel="support_page",
                page_path="/catasto",
                impact_scope="single_user",
            ),
        ]
    )
    db.commit()
    db.close()

    summary_resp = client.get("/wiki/support/analytics/summary?days=30", headers={"Authorization": f"Bearer {token}"})
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()
    assert summary["total_requests"] == 3
    assert summary["open_requests"] == 2
    assert summary["assigned_requests"] == 1
    assert summary["resolved_requests"] == 1
    assert summary["urgent_requests"] == 1
    assert summary["high_severity_requests"] == 2
    assert summary["feature_requests"] == 1
    assert summary["bug_reports"] == 1
    assert summary["data_issues"] == 1
    assert len(summary["top_modules"]) >= 1

    series_resp = client.get("/wiki/support/analytics/series?days=30", headers={"Authorization": f"Bearer {token}"})
    assert series_resp.status_code == 200, series_resp.text
    series_payload = series_resp.json()
    assert series_payload["days"] == 30
    assert len(series_payload["items"]) >= 1
    assert series_payload["items"][0]["created_count"] >= 1


def test_support_analytics_summary_includes_origin_signals_and_duplicate_pressure() -> None:
    _create_user("supportadmin_signals", "admin")
    token = _login("supportadmin_signals")
    conversation_id = uuid.uuid4()
    canonical_id = uuid.uuid4()
    duplicate_id = uuid.uuid4()
    reopened_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add_all(
        [
            WikiRequest(
                id=canonical_id,
                user_question="Errore modulo rete in dashboard",
                category="bug_report",
                request_type="bug_report",
                status="investigating",
                priority="high",
                severity="high",
                created_by="alice",
                module_key="rete",
                page_path="/network",
                source_channel="widget",
                conversation_id=conversation_id,
            ),
            WikiRequest(
                id=duplicate_id,
                user_question="Stesso errore dashboard rete",
                category="support_request",
                request_type="bug_report",
                status="duplicate",
                priority="medium",
                severity="high",
                created_by="bob",
                module_key="rete",
                page_path="/network",
                source_channel="wiki_page",
                canonical_request_id=canonical_id,
            ),
            WikiRequest(
                id=reopened_id,
                user_question="Non riesco ancora ad accedere al modulo",
                category="support_request",
                request_type="access_issue",
                status="investigating",
                priority="urgent",
                severity="critical",
                created_by="carol",
                module_key="wiki",
                source_channel="support_page",
            ),
        ]
    )
    db.add(
        WikiToolAuditLog(
            id=uuid.uuid4(),
            username="alice",
            role="viewer",
            intent="question",
            mode="docs_only",
            tool_name="guardrail",
            module_key="rete",
            conversation_id=conversation_id,
            question_hash="hash-1",
            question_preview="errore rete",
            success=1,
            found=0,
            latency_ms=120,
            docs_source_count=0,
            evidence_count=0,
        )
    )
    db.add(
        WikiRequestEvent(
            id=uuid.uuid4(),
            request_id=reopened_id,
            event_type="reopened_by_user",
            actor_username="carol",
            from_status="resolved",
            to_status="investigating",
        )
    )
    db.commit()
    db.close()

    summary_resp = client.get("/wiki/support/analytics/summary?days=30", headers={"Authorization": f"Bearer {token}"})
    assert summary_resp.status_code == 200, summary_resp.text
    summary = summary_resp.json()
    assert summary["duplicate_requests"] == 1
    assert summary["canonical_cases"] == 1
    assert summary["reopened_requests"] == 1
    assert summary["no_match_origin_requests"] == 1
    assert summary["guardrail_origin_requests"] == 1
    assert summary["docs_only_origin_requests"] == 1
    assert any(item["key"] == "widget" for item in summary["top_source_channels"])


def test_admin_can_read_support_analytics_clusters() -> None:
    _create_user("supportadmin_clusters", "admin")
    token = _login("supportadmin_clusters")
    canonical_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add_all(
        [
            WikiRequest(
                id=canonical_id,
                user_question="La pagina rete non si apre",
                category="bug_report",
                request_type="bug_report",
                status="investigating",
                priority="high",
                severity="high",
                created_by="alice",
                module_key="rete",
                page_path="/network/devices",
            ),
            WikiRequest(
                id=uuid.uuid4(),
                user_question="Errore 500 nella pagina rete dispositivi",
                category="support_request",
                request_type="bug_report",
                status="duplicate",
                priority="medium",
                severity="high",
                created_by="bob",
                module_key="rete",
                page_path="/network/devices",
                canonical_request_id=canonical_id,
            ),
            WikiRequest(
                id=uuid.uuid4(),
                user_question="Rete dispositivi: schermata bianca",
                category="support_request",
                request_type="bug_report",
                status="new",
                priority="medium",
                severity="medium",
                created_by="carol",
                module_key="rete",
                page_path="/network/devices",
            ),
        ]
    )
    db.commit()
    db.close()

    resp = client.get("/wiki/support/analytics/clusters?days=30&limit=5", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["days"] == 30
    assert len(payload["items"]) >= 1
    top_cluster = payload["items"][0]
    assert top_cluster["total_requests"] >= 2
    assert top_cluster["duplicate_requests"] >= 1
    assert top_cluster["affected_users"] >= 2
    assert len(top_cluster["sample_questions"]) >= 1


def test_viewer_cannot_read_support_analytics() -> None:
    _create_user("helpdesk_viewer", "viewer")
    token = _login("helpdesk_viewer")

    resp = client.get("/wiki/support/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
