"""
Test API chat: POST /wiki/chat.
answer_question e is_wiki_available sono mockati per non chiamare codex-lb nei test.
"""

from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import get_db
from app.core.security import hash_password
from app.db.base import Base
from app.main import app
from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse, WikiChunkSource


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


def _create_user(username: str = "user", role: str = "viewer") -> None:
    db = TestingSessionLocal()
    db.add(ApplicationUser(
        username=username,
        email=f"{username}@test.local",
        password_hash=hash_password("pass123"),
        role=role,
        is_active=True,
    ))
    db.commit()
    db.close()


def _login(username: str) -> str:
    resp = client.post("/auth/login", json={"username": username, "password": "pass123"})
    assert resp.status_code == 200
    return resp.json()["access_token"]


_MOCK_RESPONSE = WikiChatResponse(
    answer="GAIA è la piattaforma IT governance del Consorzio.",
    sources=[WikiChunkSource(source_file="ARCHITECTURE.md", section_title="Intro", excerpt="...")],
    found=True,
)

_NOT_FOUND_RESPONSE = WikiChatResponse(
    answer="Non ho trovato documenti rilevanti.",
    sources=[],
    found=False,
)


# ── autenticazione ────────────────────────────────────────────────────────────

def test_chat_unauthenticated_returns_401() -> None:
    resp = client.post("/wiki/chat", json={"question": "Cos'è GAIA?"})
    assert resp.status_code == 401


# ── disponibilità codex-lb ─────────────────────────────────────────────────────

def test_chat_returns_503_when_codex_lb_unavailable() -> None:
    _create_user("u1")
    token = _login("u1")

    with patch("app.modules.wiki.routes.chat.is_wiki_available", return_value=False):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Cos'è GAIA?"},
        )
    assert resp.status_code == 503
    assert "codex-lb" in resp.json()["detail"].lower() or "wiki" in resp.json()["detail"].lower()


# ── risposta corretta ─────────────────────────────────────────────────────────

def test_chat_returns_answer_and_sources() -> None:
    _create_user("u2")
    token = _login("u2")

    with (
        patch("app.modules.wiki.routes.chat.is_wiki_available", return_value=True),
        patch("app.modules.wiki.routes.chat.answer_question", return_value=_MOCK_RESPONSE),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Cos'è GAIA?"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is True
    assert "GAIA" in data["answer"]
    assert len(data["sources"]) == 1
    assert data["sources"][0]["source_file"] == "ARCHITECTURE.md"


def test_chat_found_false_when_no_relevant_docs() -> None:
    _create_user("u3")
    token = _login("u3")

    with (
        patch("app.modules.wiki.routes.chat.is_wiki_available", return_value=True),
        patch("app.modules.wiki.routes.chat.answer_question", return_value=_NOT_FOUND_RESPONSE),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Feature inesistente"},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["found"] is False
    assert data["sources"] == []


def test_chat_passes_context_article_to_rag() -> None:
    _create_user("u4")
    token = _login("u4")

    with (
        patch("app.modules.wiki.routes.chat.is_wiki_available", return_value=True),
        patch("app.modules.wiki.routes.chat.answer_question", return_value=_MOCK_RESPONSE) as mock_aq,
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Domanda", "context_article": "PRD.md"},
        )

    assert resp.status_code == 200
    call_args = mock_aq.call_args
    assert call_args[0][2] == "PRD.md"  # terzo argomento posizionale = context_article


def test_chat_internal_error_returns_500() -> None:
    _create_user("u5")
    token = _login("u5")

    with (
        patch("app.modules.wiki.routes.chat.is_wiki_available", return_value=True),
        patch("app.modules.wiki.routes.chat.answer_question", side_effect=Exception("errore interno")),
    ):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": "Domanda"},
        )

    assert resp.status_code == 500


def test_chat_empty_question_returns_422() -> None:
    _create_user("u6")
    token = _login("u6")

    with patch("app.modules.wiki.routes.chat.is_wiki_available", return_value=True):
        resp = client.post(
            "/wiki/chat",
            headers={"Authorization": f"Bearer {token}"},
            json={"question": ""},
        )
    assert resp.status_code == 422


def test_chat_all_user_roles_can_use() -> None:
    """Tutti i ruoli autenticati possono usare la chat."""
    for role in ("viewer", "reviewer", "admin", "super_admin"):
        username = f"role_{role}"
        _create_user(username, role)
        token = _login(username)

        with (
            patch("app.modules.wiki.routes.chat.is_wiki_available", return_value=True),
            patch("app.modules.wiki.routes.chat.answer_question", return_value=_MOCK_RESPONSE),
        ):
            resp = client.post(
                "/wiki/chat",
                headers={"Authorization": f"Bearer {token}"},
                json={"question": "Test"},
            )
        assert resp.status_code == 200, f"Role {role} got {resp.status_code}"
