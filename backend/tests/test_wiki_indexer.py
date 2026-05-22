"""
Test dell'indicizzatore Wiki: logica Python pura, nessun DB, nessuna API esterna.
Copre: _split_by_heading, _sub_chunk, _find_docs.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from app.modules.wiki.services.indexer import (
    MAX_CHUNK_CHARS,
    OVERLAP_CHARS,
    _find_docs,
    _split_code_content,
    _split_by_heading,
    _sub_chunk,
)


# ── _split_by_heading ─────────────────────────────────────────────────────────

def test_split_no_heading_returns_single_chunk() -> None:
    content = "Testo senza heading.\nSeconda riga."
    chunks = _split_by_heading(content)
    assert len(chunks) == 1
    assert chunks[0]["section_title"] is None
    assert "Testo senza heading" in chunks[0]["content"]


def test_split_single_heading() -> None:
    content = "## Titolo\nContenuto sezione."
    chunks = _split_by_heading(content)
    assert len(chunks) == 1
    assert chunks[0]["section_title"] == "Titolo"
    assert "Contenuto sezione" in chunks[0]["content"]


def test_split_multiple_headings() -> None:
    content = "## Prima sezione\nContenuto A.\n\n## Seconda sezione\nContenuto B."
    chunks = _split_by_heading(content)
    assert len(chunks) == 2
    assert chunks[0]["section_title"] == "Prima sezione"
    assert chunks[1]["section_title"] == "Seconda sezione"
    assert "Contenuto A" in chunks[0]["content"]
    assert "Contenuto B" in chunks[1]["content"]


def test_split_preamble_before_first_heading() -> None:
    content = "Introduzione.\n\n## Sezione\nContenuto."
    chunks = _split_by_heading(content)
    assert len(chunks) == 2
    assert chunks[0]["section_title"] is None
    assert "Introduzione" in chunks[0]["content"]
    assert chunks[1]["section_title"] == "Sezione"


def test_split_h1_and_h3_headings() -> None:
    content = "# Top\nIntro.\n\n### Sub\nDettagli."
    chunks = _split_by_heading(content)
    assert len(chunks) == 2
    assert chunks[0]["section_title"] == "Top"
    assert chunks[1]["section_title"] == "Sub"


def test_split_empty_section_is_skipped() -> None:
    content = "## Sezione A\n\n## Sezione B\nContenuto B."
    chunks = _split_by_heading(content)
    # Sezione A vuota deve essere saltata
    assert all(c["section_title"] != "Sezione A" for c in chunks)
    assert any(c["section_title"] == "Sezione B" for c in chunks)


def test_split_empty_content_returns_empty() -> None:
    chunks = _split_by_heading("")
    assert chunks == [] or all(c["content"] == "" for c in chunks)


# ── _sub_chunk ────────────────────────────────────────────────────────────────

def test_sub_chunk_small_content_unchanged() -> None:
    raw = [{"section_title": "A", "content": "Breve."}]
    result = _sub_chunk(raw)
    assert len(result) == 1
    assert result[0]["content"] == "Breve."


def test_sub_chunk_large_content_splits() -> None:
    long_text = "Paragrafo.\n\n" * (MAX_CHUNK_CHARS // 12 + 5)
    raw = [{"section_title": "Lunga", "content": long_text}]
    result = _sub_chunk(raw)
    assert len(result) > 1
    for chunk in result:
        assert len(chunk["content"]) <= MAX_CHUNK_CHARS + OVERLAP_CHARS + 50


def test_sub_chunk_preserves_section_title() -> None:
    long_text = "Parola.\n\n" * (MAX_CHUNK_CHARS // 9 + 10)
    raw = [{"section_title": "Titolo", "content": long_text}]
    result = _sub_chunk(raw)
    assert all(c["section_title"] == "Titolo" for c in result)


def test_sub_chunk_multiple_inputs_preserved() -> None:
    raw = [
        {"section_title": "A", "content": "Breve A."},
        {"section_title": "B", "content": "Breve B."},
    ]
    result = _sub_chunk(raw)
    assert len(result) == 2


def test_split_code_content_breaks_on_symbols() -> None:
    content = "def first():\n    return 1\n\n\ndef second():\n    return 2\n"
    result = _split_code_content(content)
    assert len(result) == 2
    assert result[0]["section_title"] == "def first():"
    assert "return 1" in result[0]["content"]
    assert result[1]["section_title"] == "def second():"


# ── _find_docs ────────────────────────────────────────────────────────────────

def test_find_docs_finds_md_files() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "README.md").write_text("# Readme")
        (root / "docs" / "NOTES.md").write_text("# Notes")
        (root / "backend" / "app").mkdir(parents=True)
        (root / "backend" / "app" / "script.py").write_text("# python")

        docs = _find_docs(root)
        names = [str(d.relative_to(root)) for d in docs]
        assert "docs/README.md" in names
        assert "docs/NOTES.md" in names
        assert "backend/app/script.py" in names


def test_find_docs_excludes_node_modules() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        nm = root / "node_modules" / "pkg"
        nm.mkdir(parents=True)
        (nm / "README.md").write_text("pkg readme")
        (root / "docs").mkdir(parents=True)
        (root / "docs" / "TOP.md").write_text("top")

        docs = _find_docs(root)
        names = [str(d.relative_to(root)) for d in docs]
        assert "README.md" not in names
        assert "docs/TOP.md" in names


def test_find_docs_recurses_domain_docs() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        dd = root / "domain-docs" / "catasto"
        dd.mkdir(parents=True)
        (dd / "PRD.md").write_text("# Catasto PRD")

        docs = _find_docs(root)
        names = [d.name for d in docs]
        assert "PRD.md" in names


def test_find_docs_no_files_returns_empty() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        docs = _find_docs(Path(tmp))
        assert docs == []
