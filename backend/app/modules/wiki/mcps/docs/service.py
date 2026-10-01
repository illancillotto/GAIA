"""Bounded source tools backed by a local SQLite FTS5 baseline."""

from __future__ import annotations

import json
import logging
import re
import sqlite3
from collections import Counter
from datetime import UTC, datetime
from time import perf_counter
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from ..context import CallContext
from .corpus import Corpus, digest, estimated_tokens, validate_source_path

logger = logging.getLogger(__name__)
SERVER_VERSION = "gaia-docs-mcp-v1"
Domain = Literal["catasto", "utenze", "ruolo", "wiki", "platform"]
Category = Literal["architecture", "procedure", "runbook", "prd", "workflow"]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class SearchInput(Input):
    query: str = Field(min_length=1, max_length=2000)
    domain: Domain | None = None
    category: Category | None = None
    limit: int = Field(default=5, ge=1, le=10)


class SectionInput(Input):
    chunk_id: str = Field(min_length=1, max_length=80)
    max_chars: int = Field(default=6000, ge=1, le=6000)


class MetadataInput(Input):
    source_path: str = Field(min_length=1, max_length=600)


INPUTS = {
    "search_docs": SearchInput,
    "get_doc_section": SectionInput,
    "get_document_metadata": MetadataInput,
    "list_doc_domains": Input,
}


class DocsService:
    def __init__(self, corpus: Corpus):
        self.corpus = corpus
        self.chunks = {chunk.chunk_id: chunk for chunk in corpus.chunks}
        self.documents = {entry.path: entry for entry in corpus.manifest.entries if entry.included}
        self.index = sqlite3.connect(":memory:", check_same_thread=False)
        self.index.execute(
            "CREATE VIRTUAL TABLE docs USING fts5(chunk_id UNINDEXED, domain UNINDEXED, "
            "category UNINDEXED, title, section, content, tokenize='unicode61')"
        )
        self.index.executemany(
            "INSERT INTO docs VALUES (?, ?, ?, ?, ?, ?)",
            [
                (
                    chunk.chunk_id,
                    self.documents[chunk.source_path].domain,
                    self.documents[chunk.source_path].category,
                    chunk.title,
                    chunk.section,
                    chunk.content,
                )
                for chunk in corpus.chunks
            ],
        )
        self.index.commit()

    def close(self) -> None:
        self.index.close()

    def _evidence(self, chunk_id: str) -> dict:
        chunk = self.chunks[chunk_id]
        entry = self.documents[chunk.source_path]
        return {
            **chunk.model_dump(),
            "domain": entry.domain,
            "category": entry.category,
            "corpus_version": self.corpus.corpus_version,
        }

    def search_docs(self, query: str, domain=None, category=None, limit=5) -> tuple[list, bool]:
        terms = list(dict.fromkeys(re.findall(r"[^\W_]+", query.lower())))[:64]
        if not terms:
            return [], False
        expression = " OR ".join(f'"{term}"' for term in terms)
        rows = self.index.execute(
            "SELECT chunk_id, bm25(docs, 0, 0, 0, 2, 2, 1) AS rank FROM docs "
            "WHERE docs MATCH ? AND (? IS NULL OR domain = ?) "
            "AND (? IS NULL OR category = ?) ORDER BY rank, chunk_id LIMIT ?",
            (expression, domain, domain, category, category, limit + 1),
        ).fetchall()
        return [
            dict(self._evidence(chunk_id), score=-rank) for chunk_id, rank in rows[:limit]
        ], len(rows) > limit

    def get_doc_section(self, chunk_id: str, max_chars=6000) -> tuple[list, bool]:
        if chunk_id not in self.chunks:
            raise ValueError("Document section unavailable")
        evidence = self._evidence(chunk_id)
        content = evidence["content"]
        evidence["content"] = content[:max_chars]
        evidence["estimated_tokens"] = estimated_tokens(evidence["content"])
        return [evidence], len(content) > max_chars

    def get_document_metadata(self, source_path: str) -> tuple[list, bool]:
        validate_source_path(source_path)
        entry = self.documents.get(source_path)
        if entry is None:
            raise ValueError("Document metadata unavailable")
        chunks = [chunk for chunk in self.chunks.values() if chunk.source_path == source_path]
        sections = [{"chunk_id": chunk.chunk_id, "section": chunk.section} for chunk in chunks]
        return [
            {
                "source_path": source_path,
                "title": chunks[0].title if chunks else "",
                "domain": entry.domain,
                "category": entry.category,
                "status": entry.status,
                "document_hash": entry.sha256,
                "corpus_version": self.corpus.corpus_version,
                "sections": sections[:100],
                "section_count": len(sections),
            }
        ], len(sections) > 100

    def list_doc_domains(self) -> tuple[list, bool]:
        documents = Counter(entry.domain for entry in self.documents.values())
        chunks = Counter(self.documents[chunk.source_path].domain for chunk in self.chunks.values())
        return [
            {"domain": domain, "document_count": documents[domain], "chunk_count": chunks[domain]}
            for domain in sorted(documents)
        ], False

    def call(self, tool_name: str, arguments: dict, *, context: CallContext | None = None) -> dict:
        context = context or CallContext(principal="local-stdio", scopes=frozenset({"docs.read"}))
        request_id = context.request_id
        started = perf_counter()
        event = {
            "request_id": request_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "principal": digest(context.principal.encode())[:24],
            "conversation_id": context.conversation_id,
            "experiment_run_id": context.experiment_run_id,
            "tool_name": tool_name if tool_name in INPUTS else "unknown",
            "source": "gaia_docs",
            "permission_scope": "docs.read",
            "server_version": SERVER_VERSION,
            "dataset_or_corpus_version": self.corpus.corpus_version,
            "status": "error",
            "result_count": 0,
            "truncated": False,
            "estimated_output_tokens": 0,
        }
        try:
            if "docs.read" not in context.scopes:
                raise PermissionError("PERMISSION_DENIED")
            if tool_name not in INPUTS:
                raise ValueError("Unknown documentation tool")
            validated = INPUTS[tool_name].model_validate(arguments)
            results, truncated = getattr(self, tool_name)(**validated.model_dump())
            provenance = [
                {
                    key: result[key]
                    for key in (
                        "source_path",
                        "chunk_id",
                        "section",
                        "document_hash",
                        "corpus_version",
                    )
                    if key in result
                }
                for result in results
            ]
            response = {
                "tool": tool_name,
                "source": "gaia_docs",
                "results": results,
                "provenance": provenance,
                "result_count": len(results),
                "truncated": truncated,
                "request_id": request_id,
                "corpus_version": self.corpus.corpus_version,
                "server_version": SERVER_VERSION,
            }
            response["estimated_tokens"] = estimated_tokens(
                json.dumps(response, ensure_ascii=False)
            )
            event.update(
                status="ok",
                result_count=len(results),
                truncated=truncated,
                estimated_output_tokens=response["estimated_tokens"],
            )
            return response
        except Exception as exc:
            event["error"] = type(exc).__name__
            raise
        finally:
            event["duration_ms"] = round((perf_counter() - started) * 1000, 3)
            logger.info("gaia_docs_mcp_call", extra={"mcp_event": event})
