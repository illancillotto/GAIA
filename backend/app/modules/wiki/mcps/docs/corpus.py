"""Reviewed manifest, deterministic Markdown chunking and frozen corpus."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Literal
from uuid import NAMESPACE_URL, uuid5

from pydantic import BaseModel, ConfigDict, Field

FORMAT_VERSION = "gaia-docs-v1"
MAX_CHUNK_CHARS = 2000
MAX_DOCUMENT_BYTES = 1_000_000
DOMAINS = {"catasto", "utenze", "ruolo", "wiki", "platform"}
BLOCKED_PARTS = {"archive", "progress", "graphify-out", "secrets", "code-quality"}
BLOCKED_NAMES = re.compile(
    r"PROMPT|CODE_SIZE|COVERAGE|REFACTOR|PROGRESS|EXECUTION|IMPLEMENTATION_PLAN|DUMP",
    re.IGNORECASE,
)
HEADING = re.compile(r"^(#{1,6})\s+(.+?)\s*#*\s*$")
FENCE = re.compile(r"^\s{0,3}(`{3,}|~{3,})")


class ManifestEntry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    path: str = Field(min_length=1, max_length=600)
    domain: Literal["catasto", "utenze", "ruolo", "wiki", "platform"]
    category: Literal["architecture", "procedure", "runbook", "prd", "workflow"]
    status: Literal["current", "historical", "deprecated", "uncertain"]
    included: bool = False
    reason: str = Field(min_length=1, max_length=1000)
    sha256: str | None = None


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    entries: list[ManifestEntry] = Field(max_length=200)


class Chunk(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    chunk_id: str
    source_path: str
    title: str
    section: str | None
    content: str = Field(min_length=1, max_length=MAX_CHUNK_CHARS)
    chunk_index: int
    document_hash: str
    estimated_tokens: int


class Corpus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format_version: Literal["gaia-docs-v1"] = FORMAT_VERSION
    corpus_version: str
    manifest: Manifest
    chunks: list[Chunk]


def canonical_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def estimated_tokens(content: str) -> int:
    return (len(content) + 3) // 4


def validate_source_path(source_path: str) -> PurePosixPath:
    path = PurePosixPath(source_path)
    if path.is_absolute() or ".." in path.parts or "\\" in source_path or "\x00" in source_path:
        raise ValueError("Invalid document path")
    if path.as_posix() != source_path or path.suffix != ".md":
        raise ValueError("Expected a canonical Markdown path")
    if not path.parts or path.parts[0] not in {"docs", "domain-docs"}:
        raise ValueError("Document outside the allowed corpus roots")
    return path


def policy_reason(entry: ManifestEntry) -> str | None:
    path = validate_source_path(entry.path)
    if any(part.lower() in BLOCKED_PARTS or part.startswith(".") for part in path.parts):
        return "Excluded directory"
    if BLOCKED_NAMES.search(path.name):
        return "Development or generated document"
    if "operational" in path.parts:
        return "Operational Wiki requires a separate experimental freeze"
    if entry.status != "current":
        return "Only reviewed current documents are eligible"
    expected_domain = "platform" if path.parts[0] == "docs" else path.parts[1]
    if expected_domain != entry.domain:
        raise ValueError("Document domain does not match its path")
    return None


def markdown_sections(content: str) -> list[tuple[str | None, str]]:
    sections: list[tuple[str | None, str]] = []
    section: str | None = None
    lines: list[str] = []
    fence: str | None = None
    for line in content.splitlines():
        marker = FENCE.match(line)
        if marker:
            delimiter = marker.group(1)
            if fence is None:
                fence = delimiter
            elif delimiter[0] == fence[0] and len(delimiter) >= len(fence):
                fence = None
        heading = HEADING.match(line) if fence is None and marker is None else None
        if heading:
            sections.append((section, "\n".join(lines).strip()))
            section = heading.group(2)[:300]
            lines = [line]
        else:
            lines.append(line)
    sections.append((section, "\n".join(lines).strip()))
    return [(section, body) for section, body in sections if body]


def chunk_document(entry: ManifestEntry, content: str) -> list[Chunk]:
    sections = markdown_sections(content)
    title = next((section for section, _body in sections if section), Path(entry.path).stem)
    chunks: list[Chunk] = []
    for section, body in sections:
        for offset in range(0, len(body), MAX_CHUNK_CHARS):
            fragment = body[offset : offset + MAX_CHUNK_CHARS].strip()
            if not fragment:
                continue
            index = len(chunks)
            identity = f"{FORMAT_VERSION}:{entry.path}:{entry.sha256}:{index}"
            chunks.append(
                Chunk(
                    chunk_id=str(uuid5(NAMESPACE_URL, identity)),
                    source_path=entry.path,
                    title=title,
                    section=section,
                    content=fragment,
                    chunk_index=index,
                    document_hash=entry.sha256,
                    estimated_tokens=estimated_tokens(fragment),
                )
            )
    return chunks


def corpus_digest(manifest: Manifest, chunks: list[Chunk]) -> str:
    payload = {
        "format_version": FORMAT_VERSION,
        "manifest": manifest.model_dump(),
        "chunks": [chunk.model_dump() for chunk in chunks],
    }
    return digest(canonical_json(payload).encode("utf-8"))


def read_reviewed_document(root: Path, entry: ManifestEntry) -> tuple[str, str, int]:
    path = (root / entry.path).resolve(strict=True)
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError("Document escapes the repository or is not a file")
    if path.stat().st_size > MAX_DOCUMENT_BYTES:
        raise ValueError("Document exceeds the size budget")
    raw = path.read_bytes()
    document_hash = digest(raw)
    if entry.sha256 is not None and entry.sha256 != document_hash:
        raise ValueError("Reviewed document hash has changed")
    return raw.decode("utf-8"), document_hash, len(raw)


def build_corpus(root: Path, manifest: Manifest) -> Corpus:
    root = root.resolve(strict=True)
    entries: list[ManifestEntry] = []
    chunks: list[Chunk] = []
    seen: set[str] = set()
    total_bytes = 0
    for entry in sorted(manifest.entries, key=lambda item: item.path):
        exclusion = policy_reason(entry)
        if entry.path in seen:
            raise ValueError("Duplicate document in manifest")
        seen.add(entry.path)
        if exclusion or not entry.included:
            entries.append(
                entry.model_copy(
                    update={"included": False, "sha256": None, "reason": exclusion or entry.reason}
                )
            )
            continue
        content, document_hash, size = read_reviewed_document(root, entry)
        total_bytes += size
        if total_bytes > 10_000_000:
            raise ValueError("Corpus exceeds the size budget")
        frozen = entry.model_copy(update={"sha256": document_hash})
        entries.append(frozen)
        chunks.extend(chunk_document(frozen, content))
    frozen_manifest = Manifest(entries=entries)
    return Corpus(
        corpus_version=corpus_digest(frozen_manifest, chunks),
        manifest=frozen_manifest,
        chunks=chunks,
    )


def load_corpus(path: Path) -> Corpus:
    if path.stat().st_size > 30_000_000:
        raise ValueError("Frozen corpus exceeds the size budget")
    corpus = Corpus.model_validate_json(path.read_bytes())
    if corpus.corpus_version != corpus_digest(corpus.manifest, corpus.chunks):
        raise ValueError("Frozen corpus integrity check failed")
    approved = {}
    for entry in corpus.manifest.entries:
        if entry.included:
            if policy_reason(entry) or entry.path in approved:
                raise ValueError("Frozen corpus violates the manifest policy")
            approved[entry.path] = entry.sha256
    identities = set()
    for chunk in corpus.chunks:
        if chunk.source_path not in approved or approved[chunk.source_path] != chunk.document_hash:
            raise ValueError("Chunk outside the approved manifest")
        if chunk.chunk_id in identities:
            raise ValueError("Duplicate chunk ID")
        identities.add(chunk.chunk_id)
    return corpus
