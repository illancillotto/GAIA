"""
Indicizzatore documenti GAIA.
Scansiona i file .md del progetto, li divide in chunk per heading,
popola la colonna search_vector via PostgreSQL FTS (nessuna chiamata API esterna).

Esecuzione:
    make wiki-index
    # oppure dal container:
    docker compose exec backend python -m app.modules.wiki.services.indexer
"""

from __future__ import annotations

import logging
import os
import re
import uuid
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.modules.wiki.models import WikiChunk

logger = logging.getLogger(__name__)

DOCS_ROOT = Path(os.environ.get("WIKI_DOCS_ROOT", "/app"))

INCLUDE_PATTERNS = [
    "docs/**/*.md",
    "domain-docs/**/*.md",
    "progress/*.md",
    "backend/app/**/*.py",
    "backend/scripts/**/*.py",
    "frontend/src/**/*.ts",
    "frontend/src/**/*.tsx",
    "modules/elaborazioni/worker/**/*.py",
]

EXCLUDE_PARTS = {
    "node_modules",
    ".next",
    "__pycache__",
    ".git",
    "venv",
    ".venv",
}

MAX_CHUNK_CHARS = 2000
OVERLAP_CHARS = 200


def _find_docs(root: Path) -> list[Path]:
    found: list[Path] = []
    for pattern in INCLUDE_PATTERNS:
        for p in root.glob(pattern):
            if any(ex in p.parts for ex in EXCLUDE_PARTS):
                continue
            if p.is_file():
                found.append(p)
    return sorted(set(found))


def _is_markdown_file(path: Path) -> bool:
    return path.suffix.lower() == ".md"


def _split_by_heading(content: str) -> list[dict]:
    heading_re = re.compile(r"^(#{1,3})\s+(.+)$", re.MULTILINE)
    chunks: list[dict] = []

    matches = list(heading_re.finditer(content))
    if not matches:
        chunks.append({"section_title": None, "content": content.strip()})
        return chunks

    preamble = content[: matches[0].start()].strip()
    if preamble:
        chunks.append({"section_title": None, "content": preamble})

    for i, match in enumerate(matches):
        section_title = match.group(2).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        section_content = content[start:end].strip()
        if section_content:
            chunks.append({"section_title": section_title, "content": section_content})

    return chunks


def _split_code_content(content: str) -> list[dict]:
    lines = content.splitlines()
    if not lines:
        return []

    chunks: list[dict] = []
    current_lines: list[str] = []
    current_title: str | None = None

    def flush() -> None:
        nonlocal current_lines, current_title
        body = "\n".join(current_lines).strip()
        if body:
            chunks.append({"section_title": current_title, "content": body})
        current_lines = []
        current_title = None

    symbol_re = re.compile(
        r"^\s*(def |class |async def |export function |export const |export default function |function |const [A-Z_a-z0-9]+\s*=)"
    )

    for line in lines:
        if symbol_re.match(line) and current_lines:
            flush()
            current_title = line.strip()[:120]
        elif current_title is None and symbol_re.match(line):
            current_title = line.strip()[:120]
        current_lines.append(line)

        if sum(len(item) + 1 for item in current_lines) >= MAX_CHUNK_CHARS:
            flush()

    flush()
    return chunks


def _sub_chunk(raw_chunks: list[dict]) -> list[dict]:
    result: list[dict] = []
    for raw in raw_chunks:
        text_body = raw["content"]
        if len(text_body) <= MAX_CHUNK_CHARS:
            result.append(raw)
            continue

        paragraphs = text_body.split("\n\n")
        current = ""
        for para in paragraphs:
            if len(current) + len(para) > MAX_CHUNK_CHARS and current:
                result.append({"section_title": raw["section_title"], "content": current.strip()})
                current = current[-OVERLAP_CHARS:] + "\n\n" + para
            else:
                current += ("\n\n" if current else "") + para
        if current.strip():
            result.append({"section_title": raw["section_title"], "content": current.strip()})

    return result


def index_documents(db: Session, force: bool = False) -> dict:
    """
    Indicizza tutti i documenti trovati.
    Popola WikiChunk.search_vector con to_tsvector('simple', content).
    Nessuna chiamata API esterna.
    """
    if force:
        db.query(WikiChunk).delete()
        db.commit()
        logger.info("wiki_chunks svuotato (force=True)")

    docs = _find_docs(DOCS_ROOT)
    logger.info("Trovati %d file da indicizzare in %s", len(docs), DOCS_ROOT)

    indexed_files: list[str] = []
    total_chunks = 0

    for doc_path in docs:
        source_file = str(doc_path.relative_to(DOCS_ROOT))
        try:
            content = doc_path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            logger.warning("Impossibile leggere %s: %s", doc_path, exc)
            continue

        raw_chunks = _split_by_heading(content) if _is_markdown_file(doc_path) else _split_code_content(content)
        chunks = _sub_chunk(raw_chunks)

        if not chunks:
            continue

        db.query(WikiChunk).filter(WikiChunk.source_file == source_file).delete()
        db.commit()

        for idx, chunk_data in enumerate(chunks):
            db.add(
                WikiChunk(
                    id=uuid.uuid4(),
                    source_file=source_file,
                    section_title=chunk_data.get("section_title"),
                    content=chunk_data["content"],
                    chunk_index=idx,
                    token_count=len(chunk_data["content"]) // 4,
                )
            )

        db.commit()

        # Aggiorna search_vector via PostgreSQL FTS (config 'simple' = no stemming language-specific)
        db.execute(
            text(
                "UPDATE wiki_chunks SET search_vector = to_tsvector('simple', content) "
                "WHERE source_file = :sf"
            ),
            {"sf": source_file},
        )
        db.commit()

        indexed_files.append(source_file)
        total_chunks += len(chunks)
        logger.info("Indicizzato: %s (%d chunk)", source_file, len(chunks))

    return {"indexed_files": indexed_files, "total_chunks": total_chunks}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    db = SessionLocal()
    try:
        result = index_documents(db, force=True)
        print(f"Indicizzati {len(result['indexed_files'])} file, {result['total_chunks']} chunk totali.")
    finally:
        db.close()
