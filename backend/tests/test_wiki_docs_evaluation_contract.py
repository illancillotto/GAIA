import json
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from app.modules.wiki.mcps import evaluation
from app.modules.wiki.mcps.docs.corpus import Manifest, ManifestEntry, build_corpus


def test_reviewed_scores_ranks_abstention_and_latency_are_exact(monkeypatch):
    queries = [
        {
            "id": "multi",
            "query": "first",
            "expected_source_path": "docs/a.md",
            "expected_section_contains": "STRASSE",
        },
        {
            "id": "miss",
            "query": "second",
            "expected_source_path": "docs/a.md",
            "expected_section_contains": "missing",
        },
        {"id": "abstain", "query": "third"},
        {"id": "empty-target", "query": "fourth", "expected_source_path": ""},
        {"id": "null-section", "query": "fifth", "expected_source_path": "docs/b.md"},
    ]
    responses = [
        {
            "results": [
                {"source_path": "docs/other.md"},
                {"source_path": "docs/a.md", "section": "Straße"},
                {"source_path": "docs/a.md", "section": "Other"},
                {"source_path": "docs/a.md", "section": "STRASSE details"},
            ],
            "result_count": 4,
            "estimated_tokens": 17,
        },
        {
            "results": [{"source_path": "docs/a.md", "section": "Other"}],
            "result_count": 1,
            "estimated_tokens": 18,
        },
        {"results": [], "result_count": 0, "estimated_tokens": 19},
        {
            "results": [{"source_path": "", "section": None}],
            "result_count": 1,
            "estimated_tokens": 20,
        },
        {
            "results": [{"source_path": "docs/b.md", "section": None}],
            "result_count": 1,
            "estimated_tokens": 21,
        },
    ]
    original_queries, original_responses = deepcopy(queries), deepcopy(responses)
    service = SimpleNamespace(
        corpus=SimpleNamespace(corpus_version="frozen-version"), call=Mock(side_effect=responses)
    )
    monkeypatch.setattr(
        evaluation,
        "perf_counter",
        Mock(side_effect=[0, 0.001, 1, 1.010, 2, 2.100, 3, 3.050, 4, 4.004]),
    )

    report = evaluation.evaluate_docs(service, queries)

    assert report == {
        "source": "gaia_docs",
        "corpus_version": "frozen-version",
        "query_count": 5,
        "success_rate": 3 / 5,
        "recall_at_10": 2 / 3,
        "mrr": 0.5,
        "precision_at_10": 0.5,
        "latency_ms": {"p50": 10.0, "p95": 100.0, "p99": 100.0},
        "cases": [
            {"id": "multi", "passed": True, "rank": 2, "result_count": 4, "estimated_tokens": 17},
            {
                "id": "miss",
                "passed": False,
                "rank": None,
                "result_count": 1,
                "estimated_tokens": 18,
            },
            {
                "id": "abstain",
                "passed": True,
                "rank": None,
                "result_count": 0,
                "estimated_tokens": 19,
            },
            {
                "id": "empty-target",
                "passed": False,
                "rank": 1,
                "result_count": 1,
                "estimated_tokens": 20,
            },
            {
                "id": "null-section",
                "passed": True,
                "rank": 1,
                "result_count": 1,
                "estimated_tokens": 21,
            },
        ],
    }
    assert service.call.call_args_list == [
        call("search_docs", {"query": query["query"], "limit": 10}) for query in queries
    ]
    assert queries == original_queries
    assert responses == original_responses


@pytest.mark.parametrize(
    ("target", "results", "passed"),
    [(None, [], True), (None, [{"source_path": "docs/a.md"}], False), ("docs/a.md", [], False)],
)
def test_empty_relevance_preserves_zero_denominators(target, results, passed):
    service = SimpleNamespace(
        corpus=SimpleNamespace(corpus_version="frozen-version"),
        call=Mock(
            return_value={"results": results, "result_count": len(results), "estimated_tokens": 1}
        ),
    )
    report = evaluation.evaluate_docs(
        service, [{"id": "case", "query": "query", "expected_source_path": target}]
    )
    assert report["success_rate"] == int(passed)
    assert report["recall_at_10"] == report["mrr"] == report["precision_at_10"] == 0
    assert report["cases"][0]["rank"] is None


def test_matching_source_still_requires_section_key():
    service = SimpleNamespace(call=Mock(return_value={"results": [{"source_path": "docs/a.md"}]}))
    with pytest.raises(KeyError, match="section"):
        evaluation.evaluate_docs(
            service, [{"id": "case", "query": "query", "expected_source_path": "docs/a.md"}]
        )


def test_source_error_is_not_converted_into_scoring_failure():
    failure = RuntimeError("Source unavailable")
    service = SimpleNamespace(call=Mock(side_effect=failure))
    with pytest.raises(RuntimeError) as caught:
        evaluation.evaluate_docs(service, [{"id": "case", "query": "query"}])
    assert caught.value is failure


def test_empty_docs_queryset_fails_before_timing_or_source_call(monkeypatch):
    service = SimpleNamespace(call=Mock())
    clock = Mock()
    monkeypatch.setattr(evaluation, "perf_counter", clock)
    with pytest.raises(ValueError, match="nonempty reviewed documentation query set"):
        evaluation.evaluate_docs(service, [])
    service.call.assert_not_called()
    clock.assert_not_called()


def test_offline_docs_cli_with_synthetic_reviewed_corpus(tmp_path, capsys):
    source_path = "docs/procedure.md"
    document = tmp_path / source_path
    document.parent.mkdir()
    document.write_text("# Titolo\nProcedura per la città.", encoding="utf-8")
    entry = ManifestEntry(
        path=source_path,
        domain="platform",
        category="procedure",
        status="current",
        included=True,
        reason="Reviewed synthetic fixture",
    )
    corpus = build_corpus(tmp_path, Manifest(entries=[entry]))
    artifact = tmp_path / "corpus.json"
    artifact.write_text(corpus.model_dump_json(), encoding="utf-8")
    queries = tmp_path / "queries.json"
    queries.write_text(
        json.dumps([{"id": "synthetic", "query": "città", "expected_source_path": source_path}]),
        encoding="utf-8",
    )
    output = tmp_path / "results" / "report.json"
    evaluation.main(
        ["docs", "--artifact", str(artifact), "--queries", str(queries), "--output", str(output)]
    )
    report = json.loads(output.read_text())
    assert report["query_count"] == 1
    assert report["success_rate"] == report["recall_at_10"] == report["mrr"] == 1
    assert report["corpus_version"] == corpus.corpus_version
    assert report["cases"][0]["passed"] is True
    assert json.loads(capsys.readouterr().out)["success_rate"] == 1
