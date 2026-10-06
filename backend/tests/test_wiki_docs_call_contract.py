import json
import logging

import pytest
import test_wiki_docs_mcp as fixtures

from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.docs.corpus import digest, estimated_tokens
from app.modules.wiki.mcps.docs.service import SERVER_VERSION

corpus = fixtures.corpus
docs_service = fixtures.service


@pytest.mark.parametrize(
    "tool_name", ["search_docs", "get_doc_section", "get_document_metadata", "list_doc_domains"]
)
def test_response_and_success_event_match_for_every_tool(docs_service, caplog, tool_name):
    caplog.set_level(logging.INFO)
    chunk = next(iter(docs_service.chunks.values()))
    arguments = {
        "search_docs": {"query": "particelle", "limit": 1},
        "get_doc_section": {"chunk_id": chunk.chunk_id, "max_chars": 5},
        "get_document_metadata": {"source_path": chunk.source_path},
        "list_doc_domains": {},
    }[tool_name]
    context = CallContext(
        principal="gaia:private-principal",
        scopes=frozenset({"docs.read"}),
        request_id="fixed-request",
        conversation_id="fixed-conversation",
        experiment_run_id="fixed-experiment",
    )
    response = docs_service.call(tool_name, arguments, context=context)
    assert set(response) == {
        "tool",
        "source",
        "results",
        "provenance",
        "result_count",
        "truncated",
        "request_id",
        "corpus_version",
        "server_version",
        "estimated_tokens",
    }
    assert response["tool"] == tool_name
    assert response["source"] == "gaia_docs"
    assert response["request_id"] == context.request_id
    assert response["corpus_version"] == docs_service.corpus.corpus_version
    assert response["server_version"] == SERVER_VERSION
    assert response["result_count"] == len(response["results"])
    for result, provenance in zip(response["results"], response["provenance"], strict=True):
        assert set(provenance) == set(result) & {
            "source_path",
            "chunk_id",
            "section",
            "document_hash",
            "corpus_version",
        }
        assert all(result[key] == value for key, value in provenance.items())
    without_estimate = {key: value for key, value in response.items() if key != "estimated_tokens"}
    assert response["estimated_tokens"] == estimated_tokens(
        json.dumps(without_estimate, ensure_ascii=False)
    )
    event = caplog.records[-1].mcp_event
    assert event["status"] == "ok"
    assert event["principal"] == digest(context.principal.encode())[:24]
    assert event["request_id"] == context.request_id
    assert event["conversation_id"] == context.conversation_id
    assert event["experiment_run_id"] == context.experiment_run_id
    assert event["result_count"] == response["result_count"]
    assert event["truncated"] == response["truncated"]
    assert event["estimated_output_tokens"] == response["estimated_tokens"]
    assert "error" not in event
    assert context.principal not in caplog.text


def test_empty_response_keeps_default_context_and_empty_provenance(docs_service, caplog):
    caplog.set_level(logging.INFO)
    response = docs_service.call("search_docs", {"query": "!!!"})
    assert response["results"] == response["provenance"] == []
    assert response["result_count"] == 0
    assert response["truncated"] is False
    event = caplog.records[-1].mcp_event
    assert event["status"] == "ok"
    assert event["principal"] == digest(b"local-stdio")[:24]
    assert event["request_id"] == response["request_id"]


def test_permission_denial_precedes_unknown_tool_and_invalid_input(docs_service, caplog):
    caplog.set_level(logging.INFO)
    context = CallContext("gaia:denied", frozenset(), request_id="denied-request")
    with pytest.raises(PermissionError, match="PERMISSION_DENIED"):
        docs_service.call("unknown-private-tool", {"private": object()}, context=context)
    event = caplog.records[-1].mcp_event
    assert event["tool_name"] == "unknown"
    assert event["request_id"] == context.request_id
    assert event["status"] == "error"
    assert event["error"] == "PermissionError"
    assert event["result_count"] == event["estimated_output_tokens"] == 0
    assert event["truncated"] is False
    assert "unknown-private-tool" not in caplog.text


def test_execution_failure_is_reraised_without_success_event(docs_service, caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    failure = RuntimeError("private internal failure")

    def fail(**arguments):
        raise failure

    monkeypatch.setattr(docs_service, "search_docs", fail)
    with pytest.raises(RuntimeError) as caught:
        docs_service.call("search_docs", {"query": "private query"})
    assert caught.value is failure
    event = caplog.records[-1].mcp_event
    assert event["status"] == "error"
    assert event["error"] == "RuntimeError"
    assert event["result_count"] == event["estimated_output_tokens"] == 0
    assert "private" not in caplog.text


def test_serialization_failure_keeps_error_event_defaults(docs_service, caplog, monkeypatch):
    caplog.set_level(logging.INFO)
    monkeypatch.setattr(docs_service, "list_doc_domains", lambda: ([{"domain": {"catasto"}}], True))
    with pytest.raises(TypeError):
        docs_service.call("list_doc_domains", {})
    event = caplog.records[-1].mcp_event
    assert event["status"] == "error"
    assert event["error"] == "TypeError"
    assert event["result_count"] == event["estimated_output_tokens"] == 0
    assert event["truncated"] is False
