"""
Test del pipeline RAG: retrieve_chunks e answer_question.
Le dipendenze esterne (DB FTS, codex-lb) sono mockat per isolare la logica.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.modules.wiki.models import WikiChunk
from app.modules.wiki.schemas import WikiChatResponse, WikiChunkSource
from app.modules.wiki.services.agent_fallback import AgentFallbackError
from app.modules.wiki.services.rag import (
    _build_context,
    _stream_delta_to_text,
    answer_question,
    answer_question_from_prepared,
    build_docs_response_from_prepared,
    prepare_docs_answer,
    retrieve_chunks,
    stream_answer_from_prepared,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

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


def _make_chunk(source_file: str = "README.md", content: str = "Contenuto.", idx: int = 0) -> WikiChunk:
    return WikiChunk(
        id=uuid.uuid4(),
        source_file=source_file,
        section_title="Sezione test",
        content=content,
        chunk_index=idx,
    )


# ── _build_context ────────────────────────────────────────────────────────────

def test_build_context_single_chunk() -> None:
    chunk = _make_chunk(content="Descrizione GAIA.")
    ctx = _build_context([chunk])
    assert "README.md" in ctx
    assert "Sezione test" in ctx
    assert "Descrizione GAIA." in ctx


def test_build_context_multiple_chunks_separated() -> None:
    chunks = [
        _make_chunk("A.md", "Contenuto A."),
        _make_chunk("B.md", "Contenuto B."),
    ]
    ctx = _build_context(chunks)
    assert "A.md" in ctx
    assert "B.md" in ctx
    assert "---" in ctx  # separatore


def test_build_context_empty_list_returns_empty() -> None:
    assert _build_context([]) == ""


def test_build_context_chunk_without_section_title() -> None:
    chunk = WikiChunk(
        id=uuid.uuid4(),
        source_file="DOC.md",
        section_title=None,
        content="Testo.",
        chunk_index=0,
    )
    ctx = _build_context([chunk])
    assert "DOC.md" in ctx
    assert "Testo." in ctx


def test_stream_delta_to_text_handles_string_list_and_other() -> None:
    assert _stream_delta_to_text("ciao") == "ciao"
    assert _stream_delta_to_text([type("Delta", (), {"text": "uno"})(), type("Delta", (), {"text": "due"})()]) == "unodue"
    assert _stream_delta_to_text(42) == ""


# ── retrieve_chunks ───────────────────────────────────────────────────────────

def test_retrieve_chunks_empty_fts_returns_empty_without_fallback() -> None:
    """FTS non trova nulla → nessun fallback implicito ai chunk recenti."""
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []

    result = retrieve_chunks(mock_db, "Cos'è GAIA?")

    assert isinstance(result, list)
    assert len(result) == 0
    mock_db.execute.assert_called_once()
    mock_db.query.assert_not_called()


def test_retrieve_chunks_empty_fts_can_use_recent_fallback_when_enabled() -> None:
    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = []
    mock_db.query.return_value.order_by.return_value.limit.return_value.all.return_value = []

    result = retrieve_chunks(mock_db, "Cos'è GAIA?", allow_recent_fallback=True)

    assert result == []
    mock_db.query.assert_called_once()


def test_retrieve_chunks_fts_returns_ordered_results() -> None:
    """FTS con risultati → ritorna i chunk nell'ordine di rilevanza."""
    c1_id = uuid.uuid4()
    c2_id = uuid.uuid4()
    c1 = _make_chunk("DOC.md", "GAIA è una piattaforma governance.", 0)
    c1.id = c1_id
    c2 = _make_chunk("PRD.md", "Il modulo catasto gestisce le visure.", 1)
    c2.id = c2_id

    mock_db = MagicMock()
    mock_db.execute.return_value.fetchall.return_value = [
        MagicMock(id=c1_id),
        MagicMock(id=c2_id),
    ]
    mock_db.query.return_value.filter.return_value.all.return_value = [c1, c2]

    result = retrieve_chunks(mock_db, "cos'è GAIA")

    assert len(result) == 2
    assert result[0].id == c1_id
    assert result[1].id == c2_id


# ── answer_question ───────────────────────────────────────────────────────────

def test_answer_question_no_chunks_returns_not_found(db) -> None:
    """Nessun chunk → risposta con found=False."""
    with patch("app.modules.wiki.services.rag.retrieve_chunks", return_value=[]):
        resp = answer_question(db, "Domanda senza risposta")
    assert isinstance(resp, WikiChatResponse)
    assert resp.found is False
    assert resp.sources == []
    assert "non ho trovato" in resp.answer.lower()
    assert "modulo" in resp.answer.lower() or "sezione" in resp.answer.lower()
    assert "per esempio:" in resp.answer.lower()


def test_answer_question_no_chunks_uses_page_specific_hint(db) -> None:
    with patch("app.modules.wiki.services.rag.retrieve_chunks", return_value=[]):
        resp = answer_question(
            db,
            "Domanda senza risposta",
            module_key="operazioni",
            page_path="/operazioni/pratiche",
        )

    assert resp.found is False
    assert "In questa pagina Pratiche Operazioni" in resp.answer
    assert "come leggere una pratica" in resp.answer


def test_answer_question_from_prepared_returns_not_found_for_empty_prepared() -> None:
    prepared = prepare_docs_answer(MagicMock(), "Domanda")
    resp = answer_question_from_prepared(prepared, "Domanda", module_key="wiki", page_path="/wiki")

    assert resp.found is False
    assert "non ho trovato" in resp.answer.lower()


def test_answer_question_calls_llm_with_context(db) -> None:
    """Con chunk disponibili: chiama il client LLM e restituisce la risposta."""
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")

    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Il backend usa FastAPI."

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with (
        patch("app.modules.wiki.services.rag.retrieve_chunks", return_value=[chunk]),
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
    ):
        resp = answer_question(db, "Che tecnologie usa il backend?")

    assert resp.found is True
    assert resp.answer == "Il backend usa FastAPI."
    assert len(resp.sources) >= 1
    assert resp.sources[0].source_file == "ARCH.md"
    mock_client.chat.completions.create.assert_called_once()


def test_answer_question_reraises_non_degraded_provider_error(db) -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("upstream timeout")

    with (
        patch("app.modules.wiki.services.rag.retrieve_chunks", return_value=[chunk]),
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
        patch("app.modules.wiki.services.rag.answer_with_agent_fallback", return_value="Risposta agent"),
    ):
        resp = answer_question(db, "Che tecnologie usa il backend?")

    assert resp.found is True
    assert resp.answer == "Risposta agent"


def test_answer_question_deduplicates_sources(db) -> None:
    """Più chunk dello stesso file → una sola voce nelle fonti."""
    chunks = [
        _make_chunk("DOC.md", f"Sezione {i}.", i)
        for i in range(3)
    ]

    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Risposta."
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with (
        patch("app.modules.wiki.services.rag.retrieve_chunks", return_value=chunks),
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
    ):
        resp = answer_question(db, "Domanda")

    source_files = [s.source_file for s in resp.sources]
    assert source_files.count("DOC.md") == 1


def test_answer_question_with_context_article_prepends_chunks(db) -> None:
    """context_article aggiunge i chunk dell'articolo in testa al contesto."""
    main_chunk = _make_chunk("DOC.md", "Contenuto principale.")
    article_chunk = _make_chunk("TARGET.md", "Contenuto articolo contestuale.")

    mock_completion = MagicMock()
    mock_completion.choices[0].message.content = "Risposta contestuale."
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = mock_completion

    with (
        patch("app.modules.wiki.services.rag.retrieve_chunks", return_value=[main_chunk]),
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
    ):
        db.add(article_chunk)
        db.commit()
        resp = answer_question(db, "Domanda", context_article="TARGET.md")

    assert resp.found is True
    # Il context deve includere il chunk dell'articolo TARGET.md
    call_args = mock_client.chat.completions.create.call_args
    user_message = call_args[1]["messages"][1]["content"]
    assert "TARGET.md" in user_message


def test_answer_question_returns_unavailable_when_provider_and_agent_fail(db) -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError(
        "Error code: 503 - {'error': {'message': 'No available accounts. Service is operating in degraded mode: all upstream accounts are unavailable', 'code': 'no_accounts'}}"
    )

    with (
        patch("app.modules.wiki.services.rag.retrieve_chunks", return_value=[chunk]),
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
        patch("app.modules.wiki.services.rag.answer_with_agent_fallback", side_effect=AgentFallbackError("boom")),
    ):
        resp = answer_question(db, "Che tecnologie usa il backend?")

    assert resp.found is True
    assert resp.sources[0].source_file == "ARCH.md"
    assert "wiki non e operativo" in resp.answer.lower()
    assert "apri supporto completo" in resp.answer.lower()


def test_answer_question_returns_agent_fallback_when_provider_fails(db) -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("upstream timeout")

    with (
        patch("app.modules.wiki.services.rag.retrieve_chunks", return_value=[chunk]),
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
        patch("app.modules.wiki.services.rag.answer_with_agent_fallback", return_value="Risposta agent locale"),
    ):
        resp = answer_question(db, "Che tecnologie usa il backend?")

    assert resp.found is True
    assert resp.answer == "Risposta agent locale"


def test_stream_answer_from_prepared_returns_unavailable_when_provider_and_agent_fail() -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")
    prepared = WikiChatResponse(
        answer="unused",
        sources=[WikiChunkSource(source_file="ARCH.md", section_title="Sezione test", excerpt="Il backend usa FastAPI e SQLAlchemy.")],
        found=True,
    )
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError(
        "Error code: 503 - {'error': {'message': 'No available accounts. Service is operating in degraded mode: all upstream accounts are unavailable', 'code': 'no_accounts'}}"
    )

    with (
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
        patch("app.modules.wiki.services.rag.answer_with_agent_fallback", side_effect=AgentFallbackError("boom")),
    ):
        chunks = list(
            stream_answer_from_prepared(
                type("Prepared", (), {"found": True, "chunks": [chunk], "sources": prepared.sources})(),
                "Che tecnologie usa il backend?",
            )
        )

    assert len(chunks) == 1
    assert "wiki non e operativo" in chunks[0].lower()


def test_stream_answer_from_prepared_returns_agent_fallback_when_provider_fails() -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")
    prepared = type(
        "Prepared",
        (),
        {
            "found": True,
            "chunks": [chunk],
            "sources": [WikiChunkSource(source_file="ARCH.md", section_title="Sezione test", excerpt="...")],
        },
    )()
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("upstream timeout")

    with (
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
        patch("app.modules.wiki.services.rag.answer_with_agent_fallback", return_value="Risposta agent locale"),
    ):
        chunks = list(stream_answer_from_prepared(prepared, "Che tecnologie usa il backend?"))

    assert chunks == ["Risposta agent locale"]


def test_stream_answer_from_prepared_returns_empty_when_not_found() -> None:
    prepared = type("Prepared", (), {"found": False, "chunks": [], "sources": []})()

    assert list(stream_answer_from_prepared(prepared, "Domanda")) == []


def test_stream_answer_from_prepared_yields_normal_deltas() -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")
    prepared = type(
        "Prepared",
        (),
        {
            "found": True,
            "chunks": [chunk],
            "sources": [WikiChunkSource(source_file="ARCH.md", section_title="Sezione test", excerpt="...")],
        },
    )()
    stream_chunks = [
        type("Chunk", (), {"choices": []})(),
        type("Chunk", (), {"choices": [type("Choice", (), {"delta": type("Delta", (), {"content": "ciao"})()})()]})(),
        type(
            "Chunk",
            (),
            {
                "choices": [
                    type(
                        "Choice",
                        (),
                        {
                            "delta": type(
                                "Delta",
                                (),
                                {"content": [type("Part", (), {"text": " mondo"})(), type("Part", (), {"text": None})()]},
                            )()
                        },
                    )()
                ]
            },
        )(),
    ]
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = stream_chunks

    with patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client):
        chunks = list(stream_answer_from_prepared(prepared, "Che tecnologie usa il backend?"))

    assert chunks == ["ciao", " mondo"]


def test_stream_answer_from_prepared_returns_unavailable_when_stream_interrupts_and_agent_fails() -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")
    prepared = type(
        "Prepared",
        (),
        {
            "found": True,
            "chunks": [chunk],
            "sources": [WikiChunkSource(source_file="ARCH.md", section_title="Sezione test", excerpt="...")],
        },
    )()
    def broken_stream():
        raise RuntimeError("stream interrotto")
        yield "unused"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = broken_stream()

    with (
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
        patch("app.modules.wiki.services.rag.answer_with_agent_fallback", side_effect=AgentFallbackError("boom")),
    ):
        chunks = list(stream_answer_from_prepared(prepared, "Che tecnologie usa il backend?"))

    assert len(chunks) == 1
    assert "wiki non e operativo" in chunks[0].lower()


def test_stream_answer_from_prepared_returns_agent_fallback_when_stream_interrupts_before_output() -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")
    prepared = type(
        "Prepared",
        (),
        {
            "found": True,
            "chunks": [chunk],
            "sources": [WikiChunkSource(source_file="ARCH.md", section_title="Sezione test", excerpt="...")],
        },
    )()

    def broken_stream():
        raise RuntimeError("stream interrotto")
        yield "unused"

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = broken_stream()

    with (
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
        patch("app.modules.wiki.services.rag.answer_with_agent_fallback", return_value="Risposta agent locale"),
    ):
        chunks = list(stream_answer_from_prepared(prepared, "Che tecnologie usa il backend?"))

    assert chunks == ["Risposta agent locale"]


def test_stream_answer_from_prepared_stops_after_partial_output_on_stream_interrupt() -> None:
    chunk = _make_chunk("ARCH.md", "Il backend usa FastAPI e SQLAlchemy.")
    prepared = type(
        "Prepared",
        (),
        {
            "found": True,
            "chunks": [chunk],
            "sources": [WikiChunkSource(source_file="ARCH.md", section_title="Sezione test", excerpt="...")],
        },
    )()

    def partial_stream():
        yield type("Chunk", (), {"choices": [type("Choice", (), {"delta": type("Delta", (), {"content": "ciao"})()})()]})()
        raise RuntimeError("stream interrotto")

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = partial_stream()

    with (
        patch("app.modules.wiki.services.rag.get_openai_client", return_value=mock_client),
        patch("app.modules.wiki.services.rag.answer_with_agent_fallback") as fallback_mock,
    ):
        chunks = list(stream_answer_from_prepared(prepared, "Che tecnologie usa il backend?"))

    assert chunks == ["ciao"]
    fallback_mock.assert_not_called()


def test_build_docs_response_from_prepared_returns_not_found_for_empty() -> None:
    prepared = type("Prepared", (), {"found": False, "chunks": [], "sources": []})()

    resp = build_docs_response_from_prepared(prepared, "Risposta")

    assert resp.found is False
    assert "non ho trovato" in resp.answer.lower()


def test_build_docs_response_from_prepared_returns_answer_when_found() -> None:
    source = WikiChunkSource(source_file="ARCH.md", section_title="Sezione test", excerpt="...")
    prepared = type("Prepared", (), {"found": True, "chunks": [], "sources": [source]})()

    resp = build_docs_response_from_prepared(prepared, "Risposta finale")

    assert resp.found is True
    assert resp.answer == "Risposta finale"
    assert resp.sources == [source]
