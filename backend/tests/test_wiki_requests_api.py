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
from app.modules.wiki.models import WikiRequest


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
    assert data["status"] == "pending"
    assert data["priority"] == "medium"
    assert data["category"] == "question"
    assert data["created_by"] == "alice"


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
        status="pending",
        priority="high",
        created_by="someone",
        assigned_to="mario",
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
    assert data[0]["assigned_to"] == "mario"
    assert data[0]["assigned_to_name"] == "mario"


def test_super_admin_can_list_requests() -> None:
    _create_user("superadmin", "super_admin")
    token = _login("superadmin")
    resp = client.get("/wiki/requests", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200


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
        status="pending",
        priority="medium",
    ))
    db.commit()
    db.close()

    resp = client.patch(
        f"/wiki/requests/{req_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "planned", "priority": "urgent", "assigned_to": "operator1", "admin_notes": "Pianificata per Q3."},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "planned"
    assert data["priority"] == "urgent"
    assert data["assigned_to"] == "operator1"
    assert data["admin_notes"] == "Pianificata per Q3."


def test_update_request_rejects_unknown_assignee() -> None:
    _create_user("admin_unknown", "admin")
    token = _login("admin_unknown")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(
        id=req_id,
        user_question="Feature richiesta",
        category="feature_request",
        status="pending",
        priority="medium",
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
        json={"status": "done"},
    )
    assert resp.status_code == 404


def test_viewer_cannot_update_request() -> None:
    _create_user("viewer2", "viewer")
    token = _login("viewer2")
    req_id = uuid.uuid4()

    db = TestingSessionLocal()
    db.add(WikiRequest(id=req_id, user_question="Q", category="question", status="pending"))
    db.commit()
    db.close()

    resp = client.patch(
        f"/wiki/requests/{req_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "done"},
    )
    assert resp.status_code == 403


def test_unauthenticated_cannot_update_request() -> None:
    resp = client.patch(f"/wiki/requests/{uuid.uuid4()}", json={"status": "done"})
    assert resp.status_code == 401
