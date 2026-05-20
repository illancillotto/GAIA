"""Pipeline RAG: retrieval via PostgreSQL FTS + completion via codex-lb."""

from __future__ import annotations

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.modules.wiki.models import WikiChunk
from app.modules.wiki.schemas import WikiChatResponse, WikiChunkSource
from app.modules.wiki.services.openai_client import (
    CHAT_MODEL,
    SYSTEM_PROMPT,
    TOP_K,
    get_openai_client,
)

logger = logging.getLogger(__name__)


def retrieve_chunks(db: Session, question: str, top_k: int = TOP_K) -> list[WikiChunk]:
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
        # Fallback: chunk recenti per dare comunque contesto
        logger.debug("FTS nessun risultato per '%s', uso fallback", question[:60])
        return db.query(WikiChunk).order_by(WikiChunk.created_at.desc()).limit(top_k).all()

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


def answer_question(
    db: Session,
    question: str,
    context_article: str | None = None,
) -> WikiChatResponse:
    """Esegue il pipeline RAG e restituisce la risposta con le fonti."""
    top_chunks = retrieve_chunks(db, question)

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

    if not top_chunks:
        return WikiChatResponse(
            answer=(
                "Non ho trovato documenti rilevanti per rispondere a questa domanda. "
                "Puoi registrare una richiesta e verrà presa in considerazione."
            ),
            sources=[],
            found=False,
        )

    context = _build_context(top_chunks[:TOP_K])
    user_message = f"Contesto documentale:\n\n{context}\n\n---\n\nDomanda: {question}"

    client = get_openai_client()
    completion = client.chat.completions.create(
        model=CHAT_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.2,
        max_tokens=1024,
    )

    # TODO(Codex): aggiungere streaming SSE con StreamingResponse + stream=True
    answer = completion.choices[0].message.content or ""

    sources = [
        WikiChunkSource(
            source_file=c.source_file,
            section_title=c.section_title,
            excerpt=c.content[:200],
        )
        for c in top_chunks[:3]
    ]

    seen_files: set[str] = set()
    unique_sources: list[WikiChunkSource] = []
    for s in sources:
        if s.source_file not in seen_files:
            seen_files.add(s.source_file)
            unique_sources.append(s)

    return WikiChatResponse(answer=answer, sources=unique_sources, found=True)
