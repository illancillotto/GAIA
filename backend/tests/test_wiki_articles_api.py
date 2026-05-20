"""
Test API articoli: GET /wiki/articles, GET /wiki/articles/{path}.
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
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiChunk


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


def _add_chunk(source_file: str, section_title: str | None, content: str, idx: int = 0) -> None:
    db = TestingSessionLocal()
    db.add(WikiChunk(
        id=uuid.uuid4(),
        source_file=source_file,
        section_title=section_title,
        content=content,
        chunk_index=idx,
    ))
    db.commit()
    db.close()


# ── GET /wiki/articles ────────────────────────────────────────────────────────

def test_list_articles_empty_db_returns_empty_list() -> None:
    _create_user("u1")
    token = _login("u1")
    resp = client.get("/wiki/articles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_articles_groups_by_source_file() -> None:
    _create_user("u2")
    token = _login("u2")

    _add_chunk("README.md", "Intro", "Testo A.", 0)
    _add_chunk("README.md", "Sezione", "Testo B.", 1)
    _add_chunk("ARCH.md", "Architettura", "Backend.", 0)

    resp = client.get("/wiki/articles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()

    source_files = [g["source_file"] for g in data]
    assert "README.md" in source_files
    assert "ARCH.md" in source_files

    readme_group = next(g for g in data if g["source_file"] == "README.md")
    assert len(readme_group["chunks"]) == 2


def test_list_articles_requires_auth() -> None:
    resp = client.get("/wiki/articles")
    assert resp.status_code == 401


def test_list_articles_chunk_has_excerpt() -> None:
    _create_user("u3")
    token = _login("u3")

    _add_chunk("DOC.md", "Test", "Contenuto di esempio per la verifica dell'excerpt.")

    resp = client.get("/wiki/articles", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    group = resp.json()[0]
    chunk = group["chunks"][0]
    assert "excerpt" in chunk
    assert len(chunk["excerpt"]) > 0


# ── GET /wiki/articles/{path} ─────────────────────────────────────────────────

def test_get_article_returns_all_chunks_for_file() -> None:
    _create_user("u4")
    token = _login("u4")

    _add_chunk("GUIDE.md", "Capitolo 1", "Primo capitolo.", 0)
    _add_chunk("GUIDE.md", "Capitolo 2", "Secondo capitolo.", 1)
    _add_chunk("OTHER.md", "Altro", "Altro file.", 0)

    resp = client.get("/wiki/articles/GUIDE.md", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_file"] == "GUIDE.md"
    assert len(data["chunks"]) == 2
    titles = [c["section_title"] for c in data["chunks"]]
    assert "Capitolo 1" in titles
    assert "Capitolo 2" in titles


def test_get_article_not_found_returns_empty_chunks() -> None:
    _create_user("u5")
    token = _login("u5")
    resp = client.get("/wiki/articles/NONEXISTENT.md", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["source_file"] == "NONEXISTENT.md"
    assert data["chunks"] == []


def test_get_article_chunks_ordered_by_index() -> None:
    _create_user("u6")
    token = _login("u6")

    # Inseriti in ordine inverso
    _add_chunk("ORDER.md", "C", "Terzo.", 2)
    _add_chunk("ORDER.md", "A", "Primo.", 0)
    _add_chunk("ORDER.md", "B", "Secondo.", 1)

    resp = client.get("/wiki/articles/ORDER.md", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    chunks = resp.json()["chunks"]
    assert chunks[0]["chunk_index"] == 0
    assert chunks[1]["chunk_index"] == 1
    assert chunks[2]["chunk_index"] == 2


def test_get_article_returns_full_content_in_excerpt() -> None:
    """Per la pagina /wiki, l'excerpt contiene il contenuto completo."""
    _create_user("u7")
    token = _login("u7")

    full_text = "Testo completo del documento per la visualizzazione nella pagina wiki."
    _add_chunk("FULL.md", None, full_text)

    resp = client.get("/wiki/articles/FULL.md", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    chunk = resp.json()["chunks"][0]
    assert full_text in chunk["excerpt"]
