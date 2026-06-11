from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser
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


def setup_module() -> None:
    app.dependency_overrides[get_db] = override_get_db
    Base.metadata.create_all(engine)


def teardown_module() -> None:
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)


def setup_function() -> None:
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def _create_user(username: str, role: str) -> None:
    db = TestingSessionLocal()
    db.add(
        ApplicationUser(
            username=username,
            email=f"{username}@test.local",
            password_hash=hash_password("pass123"),
            role=role,
            is_active=True,
        )
    )
    db.commit()
    db.close()


def _login(username: str) -> str:
    response = client.post("/auth/login", json={"username": username, "password": "pass123"})
    assert response.status_code == 200
    return response.json()["access_token"]


def test_support_analytics_summary_includes_delivery_bridge_metrics() -> None:
    _create_user("admin_support_analytics", "admin")
    token = _login("admin_support_analytics")

    now = datetime.now(timezone.utc)
    db = TestingSessionLocal()
    db.add_all(
        [
            WikiRequest(
                id=uuid.uuid4(),
                user_question="Feature con ticket",
                category="feature_request",
                request_type="feature_request",
                status="planned",
                priority="high",
                severity="medium",
                created_by="alice",
                external_ticket_key="GAIA-101",
                delivery_status="in_progress",
                created_at=now,
                updated_at=now,
            ),
            WikiRequest(
                id=uuid.uuid4(),
                user_question="Feature rilasciata",
                category="feature_request",
                request_type="feature_request",
                status="resolved",
                priority="medium",
                severity="medium",
                created_by="mario",
                external_ticket_url="https://tracker.example.test/browse/GAIA-102",
                delivery_status="released",
                created_at=now,
                updated_at=now,
            ),
            WikiRequest(
                id=uuid.uuid4(),
                user_question="Richiesta scartata",
                category="support_request",
                request_type="help_request",
                status="rejected",
                priority="low",
                severity="low",
                created_by="laura",
                delivery_status="wont_do",
                created_at=now,
                updated_at=now,
            ),
        ]
    )
    db.commit()
    db.close()

    response = client.get("/wiki/support/analytics/summary?days=30", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["linked_ticket_requests"] == 2
    assert payload["delivery_started_requests"] == 2
    assert payload["released_requests"] == 1
    assert payload["wont_do_requests"] == 1
    assert any(item["key"] == "in_progress" for item in payload["top_delivery_statuses"])
