"""Validazione qualitativa end-to-end del routing operativo Wiki (senza dipendere da codex-lb)."""

from __future__ import annotations

import re
import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.application_user import ApplicationUser
from app.modules.wiki.models import WikiChunk
from app.modules.wiki.services.guardrails import sanitize_operational_answer
from app.modules.wiki.services.orchestrator import answer_with_orchestration
from app.modules.wiki.services.rag import answer_question, prepare_docs_answer
from app.modules.wiki.services.rag import WikiPreparedDocsAnswer
from app.modules.wiki.schemas import WikiChunkSource

_META_PATTERNS = (
    re.compile(r"\bworkspace\b", re.IGNORECASE),
    re.compile(r"\bdocumento fornito\b", re.IGNORECASE),
    re.compile(r"\bcontesto tecnico\b", re.IGNORECASE),
    re.compile(r"\bverifico nel\b", re.IGNORECASE),
)

_SAMPLE_QUESTIONS = (
    {
        "question": "mi serve trovare un proprietario di un terreno cosa devo fare?",
        "module_key": "catasto",
        "page_path": "/catasto/particelle",
        "must_contain": ("comune", "foglio", "particella"),
        "must_not_contain": ("workspace", "documento fornito"),
    },
    {
        "question": "come funziona il modulo catasto?",
        "module_key": "wiki",
        "page_path": "/wiki",
        "must_contain": ("Catasto", "Scopo"),
        "must_not_contain": ("workspace",),
    },
    {
        "question": "cosa posso fare qui?",
        "module_key": "catasto",
        "page_path": "/catasto/letture-contatori",
        "must_contain": ("Contatori irrigui", "Scopo"),
        "must_not_contain": ("workspace",),
    },
    {
        "question": "come vedo una lettura di contatori?",
        "module_key": "catasto",
        "page_path": "/catasto/letture-contatori",
        "must_contain": ("contator",),
        "must_not_contain": ("workspace", "documento fornito"),
        "use_rag": True,
    },
    {
        "question": "dove trovo le richieste supporto wiki?",
        "module_key": "wiki",
        "page_path": "/wiki",
        "must_contain": ("/wiki/support",),
        "must_not_contain": ("workspace",),
    },
)


engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(engine)
    yield
    Base.metadata.drop_all(engine)


@pytest.fixture
def db():
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


def _user() -> ApplicationUser:
    user = ApplicationUser()
    user.username = "e2e-tester"
    user.role = "admin"
    return user


def _seed_operational_chunks(db) -> None:
    samples = (
        (
            "domain-docs/wiki/operational/pages/catasto__letture_contatori.md",
            "Scopo",
            "La pagina consente consultazione letture contatori irrigui. Filtra per contatore o periodo e apri il dettaglio lettura.",
        ),
        (
            "domain-docs/wiki/operational/modules/catasto.md",
            "Scopo",
            "Il modulo Catasto supporta particelle, GIS, anomalie e letture contatori irrigui.",
        ),
        (
            "domain-docs/wiki/operational/pages/wiki__support.md",
            "Scopo",
            "Le richieste supporto Wiki si aprono da /wiki/support con modulo, pagina e descrizione.",
        ),
    )
    for source_file, section_title, content in samples:
        db.add(
            WikiChunk(
                id=uuid.uuid4(),
                source_file=source_file,
                section_title=section_title,
                content=content,
                chunk_index=0,
            )
        )
    db.commit()


def _meter_reading_prepared() -> WikiPreparedDocsAnswer:
    chunk = WikiChunk(
        id=uuid.uuid4(),
        source_file="domain-docs/wiki/operational/pages/catasto__letture_contatori.md",
        section_title="Scopo",
        content="Apri Contatori irrigui, filtra per contatore o periodo e consulta il dettaglio lettura.",
        chunk_index=0,
    )
    return WikiPreparedDocsAnswer(
        chunks=[chunk],
        sources=[
            WikiChunkSource(
                source_file=chunk.source_file,
                section_title=chunk.section_title,
                excerpt=chunk.content[:200],
            )
        ],
        found=True,
    )


def _assert_no_meta_phrases(answer: str) -> None:
    cleaned = sanitize_operational_answer(answer)
    for pattern in _META_PATTERNS:
        assert pattern.search(cleaned) is None, f"Meta-frase rilevata in: {cleaned!r}"


@pytest.mark.parametrize("case", _SAMPLE_QUESTIONS, ids=[item["question"][:40] for item in _SAMPLE_QUESTIONS])
def test_operational_sample_questions_stay_useful_and_non_meta(db, case: dict, monkeypatch: pytest.MonkeyPatch) -> None:
    _seed_operational_chunks(db)
    monkeypatch.setattr("app.modules.wiki.services.orchestrator.is_wiki_available", lambda: False)

    if case.get("use_rag"):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = RuntimeError("offline")
        with (
            patch("app.modules.wiki.services.rag.prepare_docs_answer", return_value=_meter_reading_prepared()),
            patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
            patch(
                "app.modules.wiki.services.rag.answer_with_agent_fallback",
                return_value="Apri Contatori irrigui, filtra per contatore o periodo e consulta il dettaglio lettura.",
            ),
        ):
            response = answer_question(
                db,
                case["question"],
                module_key=case["module_key"],
                page_path=case["page_path"],
                operational_only=True,
            )
    else:
        response = answer_with_orchestration(
            db,
            _user(),
            case["question"],
            module_key=case["module_key"],
            page_path=case["page_path"],
        )

    answer_lower = response.answer.lower()
    for token in case["must_contain"]:
        assert token.lower() in answer_lower, f"Manca {token!r} in {response.answer!r}"
    for token in case["must_not_contain"]:
        assert token.lower() not in answer_lower, f"Presente {token!r} in {response.answer!r}"
    _assert_no_meta_phrases(response.answer)
