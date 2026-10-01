import csv
import json
import logging
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client
from pydantic import ValidationError

from app.modules.wiki.mcps.docs import cli
from app.modules.wiki.mcps.docs.corpus import (
    MAX_CHUNK_CHARS,
    Manifest,
    ManifestEntry,
    build_corpus,
    chunk_document,
    corpus_digest,
    digest,
    load_corpus,
    markdown_sections,
    policy_reason,
    validate_source_path,
)
from app.modules.wiki.mcps.docs.server import create_server
from app.modules.wiki.mcps.docs.service import DocsService


def entry(path="domain-docs/catasto/docs/PRD.md", **kwargs):
    return ManifestEntry(
        path=path,
        domain="catasto",
        category="prd",
        status="current",
        included=True,
        reason="Reviewed test fixture",
        **kwargs,
    )


def write_document(root, document, content):
    path = root / document.path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


@pytest.fixture
def corpus(tmp_path):
    documents = [entry(), entry("domain-docs/catasto/docs/workflow.md")]
    write_document(
        tmp_path,
        documents[0],
        "# Catasto\n\nRegistro irriguo.\n\n## Ricerca\nCercare particelle irrigue.",
    )
    write_document(tmp_path, documents[1], "# Workflow\n\n## Particelle\nParticelle del distretto.")
    return build_corpus(tmp_path, Manifest(entries=documents))


@pytest.fixture
def service(corpus):
    service = DocsService(corpus)
    yield service
    service.close()


@pytest.mark.parametrize(
    "source_path",
    [
        "/etc/passwd",
        "docs/../secrets/key.md",
        "docs\\secret.md",
        "docs/secret\x00.md",
        "docs//file.md",
        "docs/file.py",
        "backend/source.md",
        "docs/./file.md",
        "",
    ],
)
def test_rejects_unsafe_paths(source_path):
    with pytest.raises(ValueError):
        validate_source_path(source_path)


@pytest.mark.parametrize(
    "path, updates, reason",
    [
        ("domain-docs/catasto/archive/old.md", {}, "Excluded directory"),
        ("domain-docs/catasto/progress/new.md", {}, "Excluded directory"),
        ("domain-docs/catasto/graphify-out/report.md", {}, "Excluded directory"),
        ("domain-docs/catasto/.env.md", {}, "Excluded directory"),
        ("domain-docs/catasto/docs/PROMPT_CODEX.md", {}, "Development or generated document"),
        ("domain-docs/catasto/docs/TEST_COVERAGE.md", {}, "Development or generated document"),
        ("domain-docs/wiki/operational/modules/test.md", {"domain": "wiki"}, "Operational Wiki"),
        ("domain-docs/catasto/docs/old.md", {"status": "historical"}, "Only reviewed current"),
        ("domain-docs/catasto/docs/old.md", {"status": "deprecated"}, "Only reviewed current"),
        ("domain-docs/catasto/docs/old.md", {"status": "uncertain"}, "Only reviewed current"),
    ],
)
def test_policy_enforced_even_if_manifest_includes_document(path, updates, reason, tmp_path):
    document = entry(path).model_copy(update=updates)
    assert reason in policy_reason(document)
    corpus = build_corpus(tmp_path, Manifest(entries=[document]))
    assert corpus.chunks == []
    assert corpus.manifest.entries[0].included is False
    assert corpus.manifest.entries[0].sha256 is None


def test_domain_validation():
    with pytest.raises(ValueError, match="domain"):
        policy_reason(entry("domain-docs/ruolo/docs/PRD.md"))
    platform = entry("docs/ARCHITECTURE.md").model_copy(update={"domain": "platform"})
    assert policy_reason(platform) is None


def test_chunking_fences_headings_and_hard_cap():
    content = "Preamble\n# Title\n```md\n## Not a section\n~~~~\n```\n###### Last\n" + "x" * 4200
    sections = markdown_sections(content)
    assert [section for section, _body in sections] == [None, "Title", "Last"]
    assert "## Not a section" in sections[1][1]
    chunks = chunk_document(entry().model_copy(update={"sha256": "abc"}), content)
    assert all(0 < len(chunk.content) <= MAX_CHUNK_CHARS for chunk in chunks)
    assert all(chunk.title == "Title" for chunk in chunks)
    assert chunks[0].section is None
    assert len(chunks) == 5
    assert chunks == chunk_document(entry().model_copy(update={"sha256": "abc"}), content)
    assert chunk_document(entry(), "  \n  ") == []
    hashed_entry = entry().model_copy(update={"sha256": "abc"})
    assert chunk_document(hashed_entry, "plain text")[0].title == "PRD"
    assert len(chunk_document(hashed_entry, "x" * 2000 + " " * 2000 + "x")) == 2
    assert markdown_sections("~~~\n# code\n~~~~\n# Heading")[-1][0] == "Heading"
    assert markdown_sections("````\n```\n# code\n````\n# Heading")[-1][0] == "Heading"


def test_manifest_exclusion_duplicate_and_freeze(tmp_path):
    document = entry()
    excluded = entry("domain-docs/catasto/docs/private.md").model_copy(update={"included": False})
    write_document(tmp_path, document, "# Catasto\nTest")
    manifest = Manifest(entries=[excluded, document])
    first = build_corpus(tmp_path, manifest)
    second = build_corpus(tmp_path, manifest)
    assert first == second
    assert first.manifest.entries[1].reason == excluded.reason
    assert first.manifest.entries[0].sha256 == digest(b"# Catasto\nTest")
    assert build_corpus(tmp_path, first.manifest) == first
    with pytest.raises(ValueError, match="Duplicate"):
        build_corpus(tmp_path, Manifest(entries=[document, document]))
    write_document(tmp_path, document, "# Changed")
    assert build_corpus(tmp_path, manifest).corpus_version != first.corpus_version
    with pytest.raises(ValueError, match="hash has changed"):
        build_corpus(tmp_path, first.manifest)


def test_symlink_cannot_escape_root(tmp_path):
    root = tmp_path / "root"
    root.mkdir()
    outside = tmp_path / "private.md"
    outside.write_text("Secret")
    path = root / entry().path
    path.parent.mkdir(parents=True)
    path.symlink_to(outside)
    with pytest.raises(ValueError, match="escapes"):
        build_corpus(root, Manifest(entries=[entry()]))
    path.unlink()
    path.mkdir()
    with pytest.raises(ValueError, match="not a file"):
        build_corpus(root, Manifest(entries=[entry()]))


def test_corpus_budget_and_encoding(tmp_path):
    document = entry()
    write_document(tmp_path, document, "x" * 1_000_001)
    with pytest.raises(ValueError, match="Document exceeds"):
        build_corpus(tmp_path, Manifest(entries=[document]))
    documents = [entry(f"domain-docs/catasto/docs/file_{index}.md") for index in range(11)]
    for document in documents:
        write_document(tmp_path, document, "x" * 950_000)
    with pytest.raises(ValueError, match="Corpus exceeds"):
        build_corpus(tmp_path, Manifest(entries=documents))
    (tmp_path / document.path).write_bytes(b"\xff")
    with pytest.raises(UnicodeDecodeError):
        build_corpus(tmp_path, Manifest(entries=[document]))
    with pytest.raises(FileNotFoundError):
        build_corpus(tmp_path, Manifest(entries=[entry("domain-docs/catasto/docs/missing.md")]))


def save_corpus(path, corpus, recompute=True):
    if recompute:
        corpus.corpus_version = corpus_digest(corpus.manifest, corpus.chunks)
    path.write_text(corpus.model_dump_json(), encoding="utf-8")


def test_frozen_corpus_integrity(corpus, tmp_path, monkeypatch):
    path = tmp_path / "corpus.json"
    save_corpus(path, corpus)
    assert load_corpus(path) == corpus
    corrupted = corpus.model_copy(deep=True)
    corrupted.corpus_version = "wrong"
    save_corpus(path, corrupted, recompute=False)
    with pytest.raises(ValueError, match="integrity"):
        load_corpus(path)
    monkeypatch.setattr(Path, "stat", lambda self: SimpleNamespace(st_size=30_000_001))
    with pytest.raises(ValueError, match="size budget"):
        load_corpus(path)


@pytest.mark.parametrize(
    "mutation, message",
    [
        ("excluded", "outside the approved"),
        ("mismatch", "outside the approved"),
        ("duplicate_chunk", "Duplicate chunk"),
        ("duplicate_document", "violates the manifest"),
        ("historical", "violates the manifest"),
    ],
)
def test_frozen_corpus_rejects_invalid_manifest_and_chunks(corpus, tmp_path, mutation, message):
    corpus = corpus.model_copy(deep=True)
    if mutation == "excluded":
        corpus.manifest.entries[0] = corpus.manifest.entries[0].model_copy(
            update={"included": False}
        )
    elif mutation == "mismatch":
        corpus.chunks[0] = corpus.chunks[0].model_copy(update={"document_hash": "different"})
    elif mutation == "duplicate_chunk":
        corpus.chunks.append(corpus.chunks[0])
    elif mutation == "duplicate_document":
        corpus.manifest.entries.append(corpus.manifest.entries[0])
    else:
        corpus.manifest.entries[0] = corpus.manifest.entries[0].model_copy(
            update={"status": "historical"}
        )
    path = tmp_path / "corpus.json"
    save_corpus(path, corpus)
    with pytest.raises(ValueError, match=message):
        load_corpus(path)


def test_search_filters_order_provenance_and_no_answer(service):
    response = service.call("search_docs", {"query": "particelle", "limit": 1})
    assert response["result_count"] == 1
    assert response["truncated"] is True
    assert response["source"] == "gaia_docs"
    evidence = response["results"][0]
    assert evidence["score"] > 0
    assert evidence["document_hash"]
    assert evidence["corpus_version"] == response["corpus_version"]
    assert response["provenance"][0]["chunk_id"] == evidence["chunk_id"]
    assert response["estimated_tokens"] > 0
    repeated = service.call("search_docs", {"query": "particelle", "limit": 1})
    assert repeated["results"] == response["results"]
    assert repeated["request_id"] != response["request_id"]
    all_results = service.call(
        "search_docs", {"query": "particelle", "domain": "catasto", "category": "prd"}
    )
    assert all_results["result_count"] == 2
    assert all_results["truncated"] is False
    for arguments in [
        {"query": "particelle", "domain": "utenze"},
        {"query": "particelle", "category": "runbook"},
        {"query": "nessunrisultato"},
        {"query": ' "* OR () -- '},
        {"query": " "},
    ]:
        assert service.call("search_docs", arguments)["results"] == []


def test_section_metadata_domains_and_telemetry(service, caplog):
    caplog.set_level(logging.INFO)
    chunk = next(iter(service.chunks.values()))
    section = service.call("get_doc_section", {"chunk_id": chunk.chunk_id, "max_chars": 5})
    assert section["results"][0]["content"] == chunk.content[:5]
    assert section["truncated"] is True
    assert service.call("get_doc_section", {"chunk_id": chunk.chunk_id})["truncated"] is False
    metadata = service.call("get_document_metadata", {"source_path": chunk.source_path})
    assert metadata["results"][0]["title"] == chunk.title
    assert "content" not in metadata["results"][0]
    assert metadata["truncated"] is False
    domains = service.call("list_doc_domains", {})
    assert domains["results"] == [{"domain": "catasto", "document_count": 2, "chunk_count": 4}]
    event = caplog.records[-1].mcp_event
    assert event["request_id"] == domains["request_id"]
    assert event["status"] == "ok"
    assert event["permission_scope"] == "docs.read"
    assert event["duration_ms"] >= 0
    assert event["timestamp"].endswith("+00:00")
    assert "content" not in event and "query" not in event


@pytest.mark.parametrize(
    "tool, arguments, exception",
    [
        ("search_docs", {"query": "x", "limit": 11}, ValidationError),
        ("search_docs", {"query": "x", "limit": 0}, ValidationError),
        ("search_docs", {"query": "x", "limit": True}, ValidationError),
        ("search_docs", {"query": "x", "domain": "secrets"}, ValidationError),
        ("search_docs", {"query": "x" * 2001}, ValidationError),
        ("search_docs", {"query": ""}, ValidationError),
        ("search_docs", {"query": "x", "sql": "SELECT *"}, ValidationError),
        ("get_doc_section", {"chunk_id": "missing"}, ValueError),
        ("get_doc_section", {"chunk_id": "x", "max_chars": 6001}, ValidationError),
        ("get_document_metadata", {"source_path": "docs/private.md"}, ValueError),
        (
            "get_document_metadata",
            {"source_path": "domain-docs/catasto/archive/test.md"},
            ValueError,
        ),
        ("get_document_metadata", {"source_path": "docs/../secret.md"}, ValueError),
        ("execute_sql", {"sql": "SELECT secret"}, ValueError),
    ],
)
def test_invalid_calls_are_audited_without_payloads(service, caplog, tool, arguments, exception):
    caplog.set_level(logging.INFO)
    with pytest.raises(exception):
        service.call(tool, arguments)
    event = caplog.records[-1].mcp_event
    assert event["status"] == "error"
    assert event["error"] == exception.__name__
    assert event["result_count"] == 0
    assert "arguments" not in event
    assert "SELECT secret" not in caplog.text


def test_metadata_cap_and_empty_document(tmp_path):
    document = entry()
    empty = entry("domain-docs/catasto/docs/empty.md")
    write_document(
        tmp_path, document, "\n".join(f"## Section {index}\ntext" for index in range(101))
    )
    write_document(tmp_path, empty, "")
    service = DocsService(build_corpus(tmp_path, Manifest(entries=[document, empty])))
    try:
        metadata = service.call("get_document_metadata", {"source_path": document.path})
        assert metadata["truncated"] is True
        assert len(metadata["results"][0]["sections"]) == 100
        assert metadata["results"][0]["section_count"] == 101
        assert (
            service.call("get_document_metadata", {"source_path": empty.path})["results"][0][
                "title"
            ]
            == ""
        )
    finally:
        service.close()


def test_mcp_sdk_contract(service):
    async def exercise():
        server = create_server(service)
        tools = await server.list_tools()
        assert sorted(tool.name for tool in tools) == sorted(
            [
                "search_docs",
                "get_doc_section",
                "get_document_metadata",
                "list_doc_domains",
            ]
        )
        assert all(tool.annotations.read_only_hint for tool in tools)
        schema = next(tool.input_schema for tool in tools if tool.name == "search_docs")
        assert schema["properties"]["limit"]["maximum"] == 10
        search = await server.call_tool("search_docs", {"query": "particelle"})
        assert search.structured_content["result_count"] == 2
        chunk_id = search.structured_content["results"][0]["chunk_id"]
        section = await server.call_tool("get_doc_section", {"chunk_id": chunk_id})
        assert section.structured_content["result_count"] == 1
        metadata = await server.call_tool("get_document_metadata", {"source_path": entry().path})
        assert metadata.structured_content["result_count"] == 1
        domains = await server.call_tool("list_doc_domains", {})
        assert domains.structured_content["result_count"] == 1

    anyio.run(exercise)


def test_cli_artifacts_and_cleanup(tmp_path, corpus, monkeypatch, capsys):
    manifest = tmp_path / "manifest.json"
    root = tmp_path / "root"
    for document in corpus.manifest.entries:
        write_document(root, document, "# Catasto\nParticelle")
    manifest.write_text(Manifest(entries=[entry()]).model_dump_json())
    output = tmp_path / "snapshot"
    args = ["build", "--root", str(root), "--manifest", str(manifest), "--output", str(output)]
    cli.main(args)
    assert json.loads(capsys.readouterr().out)["document_count"] == 1
    with (output / "corpus_manifest.csv").open() as handle:
        assert len(list(csv.DictReader(handle))) == 1
    snapshot = (output / "corpus.json").read_bytes()
    cli.main(args)
    assert (output / "corpus.json").read_bytes() == snapshot
    assert (
        json.loads((output / "corpus_version.json").read_text())["corpus_version"]
        == load_corpus(output / "corpus.json").corpus_version
    )
    captured = {}

    def create(service):
        captured["service"] = service

        def run(transport):
            assert transport == "stdio"
            raise RuntimeError("Stopped")

        return SimpleNamespace(run=run)

    monkeypatch.setattr(cli, "create_server", create)
    with pytest.raises(RuntimeError, match="Stopped"):
        cli.main(["serve", "--corpus", str(output / "corpus.json")])
    with pytest.raises(Exception, match="closed database"):
        captured["service"].index.execute("SELECT 1")
    formatter = cli.EventFormatter()
    record = logging.LogRecord("test", logging.INFO, "", 0, "normal", (), None)
    assert json.loads(formatter.format(record)) == {"message": "normal"}
    record.mcp_event = {"status": "ok"}
    assert json.loads(formatter.format(record)) == {"status": "ok"}


def test_module_entrypoint(monkeypatch):
    called = []
    monkeypatch.setattr(cli, "main", lambda: called.append(True))
    runpy.run_module("app.modules.wiki.mcps.docs", run_name="__main__")
    assert called == [True]


def test_stdio_protocol_handshake_and_tools(tmp_path, corpus):
    path = tmp_path / "corpus.json"
    save_corpus(path, corpus)
    backend = Path(__file__).resolve().parents[1]

    async def exercise():
        params = StdioServerParameters(
            command=sys.executable,
            args=["-m", "app.modules.wiki.mcps.docs", "serve", "--corpus", str(path)],
            cwd=backend,
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                initialized = await session.initialize()
                assert initialized.protocol_version == "2025-11-25"
                assert initialized.server_info.name == "GAIA Docs MCP"
                tools = await session.list_tools()
                assert len(tools.tools) == 4
                result = await session.call_tool("search_docs", {"query": "particelle"})
                assert result.is_error is False
                assert result.structured_content["result_count"] == 2
                invalid = await session.call_tool("get_doc_section", {"chunk_id": "missing"})
                assert invalid.is_error is True
                capped = await session.call_tool("search_docs", {"query": "x", "limit": 999})
                assert capped.is_error is True

    anyio.run(exercise)
