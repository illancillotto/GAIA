"""Pipeline RAG: retrieval via PostgreSQL FTS + completion via codex-lb."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Iterator

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.wiki.models import WikiChunk
from app.modules.wiki.schemas import WikiChatResponse, WikiChunkSource
from app.modules.wiki.services.guardrails import build_page_capability_hint
from app.modules.wiki.services.agent_fallback import AgentFallbackError, answer_with_agent_fallback
from app.modules.wiki.services.openai_client import (
    CHAT_MODEL,
    SYSTEM_PROMPT,
    TOP_K,
    get_openai_client,
)

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class WikiPreparedDocsAnswer:
    chunks: list[WikiChunk]
    sources: list[WikiChunkSource]
    found: bool


def _build_not_found_response(module_key: str | None = None, page_path: str | None = None) -> WikiChatResponse:
    return WikiChatResponse(
        answer=(
            "Non ho trovato contenuti interni sufficientemente rilevanti per rispondere a questa domanda. "
            f"{build_page_capability_hint(module_key, page_path)}"
        ),
        sources=[],
        found=False,
    )


def _build_wiki_unavailable_response(
    sources: list[WikiChunkSource],
    *,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiChatResponse:
    return WikiChatResponse(
        answer=(
            "Ho trovato documenti interni pertinenti, ma in questo momento il Wiki non e operativo "
            "e non riesce a sintetizzarli. Riprova tra pochi minuti oppure usa "
            f"'Apri supporto completo' dal widget. {build_page_capability_hint(module_key, page_path)}"
        ),
        sources=sources,
        found=bool(sources),
    )


def retrieve_chunks(
    db: Session,
    question: str,
    top_k: int = TOP_K,
    *,
    allow_recent_fallback: bool = False,
) -> list[WikiChunk]:
    """
    Retrieval via PostgreSQL full-text search (plainto_tsquery, config 'simple').
    Fallback: ultimi N chunk se la query non trova risultati.
    """
    rows = db.execute(
        text("""
            SELECT id, ts_rank(search_vector, plainto_tsquery('simple', :q)) AS rank
            FROM wiki_chunks
            WHERE search_vector @@ plainto_tsquery('simple', :q)
            ORDER BY rank DESC
            LIMIT :k
        """),
        {"q": question, "k": top_k},
    ).fetchall()

    if not rows:
        if allow_recent_fallback:
            logger.debug("FTS nessun risultato per '%s', uso fallback recenti", question[:60])
            return db.query(WikiChunk).order_by(WikiChunk.created_at.desc()).limit(top_k).all()
        logger.debug("FTS nessun risultato per '%s', nessun fallback", question[:60])
        return []

    ids = [row.id for row in rows]
    chunks_by_id = {c.id: c for c in db.query(WikiChunk).filter(WikiChunk.id.in_(ids)).all()}
    return [chunks_by_id[i] for i in ids if i in chunks_by_id]


def _build_context(chunks: list[WikiChunk]) -> str:
    parts = []
    for chunk in chunks:
        header = f"[{chunk.source_file}"
        if chunk.section_title:
            header += f" — {chunk.section_title}"
        header += "]"
        parts.append(f"{header}\n{chunk.content}")
    return "\n\n---\n\n".join(parts)


def _build_sources(chunks: list[WikiChunk]) -> list[WikiChunkSource]:
    sources = [
        WikiChunkSource(
            source_file=c.source_file,
            section_title=c.section_title,
            excerpt=c.content[:200],
        )
        for c in chunks[:3]
    ]

    seen_files: set[str] = set()
    unique_sources: list[WikiChunkSource] = []
    for source in sources:
        if source.source_file not in seen_files:
            seen_files.add(source.source_file)
            unique_sources.append(source)
    return unique_sources


def prepare_docs_answer(
    db: Session,
    question: str,
    context_article: str | None = None,
    *,
    allow_recent_fallback: bool = False,
    retrieval_query: str | None = None,
) -> WikiPreparedDocsAnswer:
    retrieval_text = retrieval_query or question
    top_chunks = retrieve_chunks(db, retrieval_text, allow_recent_fallback=allow_recent_fallback)

    if context_article:
        article_chunks = (
            db.query(WikiChunk)
            .filter(WikiChunk.source_file == context_article)
            .order_by(WikiChunk.chunk_index)
            .limit(3)
            .all()
        )
        seen_ids = {c.id for c in top_chunks}
        extra = [c for c in article_chunks if c.id not in seen_ids]
        top_chunks = extra + top_chunks

    return WikiPreparedDocsAnswer(
        chunks=top_chunks[:TOP_K],
        sources=_build_sources(top_chunks[:TOP_K]),
        found=bool(top_chunks),
    )


def _stream_delta_to_text(delta: Any) -> str:
    if isinstance(delta, str):
        return delta
    if isinstance(delta, list):
        pieces: list[str] = []
        for item in delta:
            text = getattr(item, "text", None)
            if isinstance(text, str):
                pieces.append(text)
        return "".join(pieces)
    return ""


def _answer_with_local_agent(prepared: WikiPreparedDocsAnswer, question: str) -> str:
    return answer_with_agent_fallback(
        question=question,
        context=_build_context(prepared.chunks),
        system_prompt=SYSTEM_PROMPT,
    )


def stream_answer_from_prepared(prepared: WikiPreparedDocsAnswer, question: str) -> Iterator[str]:
    if not prepared.found:
        return

    context = _build_context(prepared.chunks)
    user_message = f"Contesto documentale:\n\n{context}\n\n---\n\nDomanda: {question}"

    client = get_openai_client()
    try:
        stream = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
            stream=True,
        )
    except Exception as exc:
        logger.warning("Wiki provider unavailable during streaming response: %s", exc)
        try:
            yield _answer_with_local_agent(prepared, question)
        except AgentFallbackError as fallback_exc:
            logger.warning("Wiki local agent fallback failed during streaming response: %s", fallback_exc)
            yield _build_wiki_unavailable_response(prepared.sources).answer
        return

    emitted_content = False
    try:
        for chunk in stream:
            if not getattr(chunk, "choices", None):
                continue
            delta = getattr(chunk.choices[0], "delta", None)
            content = _stream_delta_to_text(getattr(delta, "content", None))
            if content:
                emitted_content = True
                yield content
    except Exception as exc:
        logger.warning("Wiki provider stream interrupted: %s", exc)
        if emitted_content:
            return
        try:
            yield _answer_with_local_agent(prepared, question)
        except AgentFallbackError as fallback_exc:
            logger.warning("Wiki local agent fallback failed after stream interruption: %s", fallback_exc)
            yield _build_wiki_unavailable_response(prepared.sources).answer


def answer_question_from_prepared(
    prepared: WikiPreparedDocsAnswer,
    question: str,
    *,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiChatResponse:
    if not prepared.found:
        return _build_not_found_response(module_key, page_path)

    context = _build_context(prepared.chunks)
    user_message = f"Contesto documentale:\n\n{context}\n\n---\n\nDomanda: {question}"

    client = get_openai_client()
    try:
        completion = client.chat.completions.create(
            model=CHAT_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.2,
            max_tokens=1024,
        )
    except Exception as exc:
        logger.warning("Wiki provider unavailable during docs answer: %s", exc)
        try:
            answer = _answer_with_local_agent(prepared, question)
        except AgentFallbackError as fallback_exc:
            logger.warning("Wiki local agent fallback failed during docs answer: %s", fallback_exc)
            return _build_wiki_unavailable_response(
                prepared.sources,
                module_key=module_key,
                page_path=page_path,
            )
        return WikiChatResponse(answer=answer, sources=prepared.sources, found=True)

    answer = completion.choices[0].message.content or ""
    return WikiChatResponse(answer=answer, sources=prepared.sources, found=True)


def build_docs_response_from_prepared(
    prepared: WikiPreparedDocsAnswer,
    answer: str,
    *,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiChatResponse:
    if not prepared.found:
        return _build_not_found_response(module_key, page_path)
    return WikiChatResponse(answer=answer, sources=prepared.sources, found=True)


def answer_question(
    db: Session,
    question: str,
    context_article: str | None = None,
    *,
    allow_recent_fallback: bool = False,
    retrieval_query: str | None = None,
    module_key: str | None = None,
    page_path: str | None = None,
) -> WikiChatResponse:
    """Esegue il pipeline RAG e restituisce la risposta con le fonti."""
    prepared = prepare_docs_answer(
        db,
        question,
        context_article,
        allow_recent_fallback=allow_recent_fallback,
        retrieval_query=retrieval_query,
    )
    return answer_question_from_prepared(prepared, question, module_key=module_key, page_path=page_path)
