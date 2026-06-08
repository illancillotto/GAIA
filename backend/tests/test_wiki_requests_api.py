"""
Test API WikiRequest: POST /wiki/requests, GET /wiki/requests, PATCH /wiki/requests/{id}.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser, ApplicationUserRole
from app.modules.wiki.models import WikiRequest, WikiRequestEvent


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
        json={"status": "planned", "priority": "urgent", "severity": "critical", "assigned_to": "operator1", "resolution_message": "La richiesta è stata presa in carico e pianificata.", "admin_notes": "Pianificata per Q3."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "planned"
    assert data["priority"] == "urgent"
    assert data["severity"] == "critical"
    assert data["assigned_to"] == "operator1"
    assert data["resolution_message"] == "La richiesta è stata presa in carico e pianificata."
    assert data["admin_notes"] == "Pianificata per Q3."
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


def test_viewer_cannot_read_support_analytics() -> None:
    _create_user("helpdesk_viewer", "viewer")
    token = _login("helpdesk_viewer")

    resp = client.get("/wiki/support/analytics/summary", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 403
