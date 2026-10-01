import json
import runpy
import sys
from collections import Counter
from pathlib import Path

import pytest

from app.modules.wiki.mcps import evaluation
from app.modules.wiki.mcps.data.database import seed_database
from app.modules.wiki.mcps.data.service import DataService
from app.modules.wiki.mcps.docs.corpus import Manifest, build_corpus, load_corpus
from app.modules.wiki.mcps.docs.service import DocsService

ROOT = Path(__file__).resolve().parents[2]


def test_frozen_repository_corpus_and_32_reviewed_queries(tmp_path):
    manifest = Manifest.model_validate_json((ROOT / "config/mcps/docs-manifest.json").read_text())
    corpus = build_corpus(ROOT, manifest)
    service = DocsService(corpus)
    queries = json.loads((ROOT / "config/mcps/docs-queries.json").read_text())
    try:
        report = evaluation.evaluate_docs(service, queries)
        assert len(queries) == 32
        assert report["success_rate"] == 1
        assert report["recall_at_10"] == 1
        assert report["mrr"] >= 0.9
        assert (
            report["latency_ms"]["p50"]
            <= report["latency_ms"]["p95"]
            <= report["latency_ms"]["p99"]
        )
        assert len(corpus.chunks) > 0
        bad = evaluation.evaluate_docs(
            service,
            [{"id": "negative", "query": "particelle", "expected_source_path": "missing.md"}],
        )
        assert bad["success_rate"] == 0 and bad["mrr"] == 0
        abstention = evaluation.evaluate_docs(
            service, [{"id": "empty", "query": "nosuchword", "expected_source_path": None}]
        )
        assert abstention["success_rate"] == 1 and abstention["mrr"] == 0
        with pytest.raises(ValueError):
            evaluation.evaluate_docs(service, [])
    finally:
        service.close()
    path = tmp_path / "corpus.json"
    path.write_text(corpus.model_dump_json())
    assert load_corpus(path) == corpus


def test_30_structured_ground_truth_queries(tmp_path):
    path = tmp_path / "gaia-mcp-synthetic-evaluation.sqlite"
    seed_database(path, "gaia-v1")
    queries = json.loads((ROOT / "config/mcps/data-queries.json").read_text())
    assert Counter(query["category"] for query in queries) == {
        "lookup": 8,
        "relational": 8,
        "multi_hop": 6,
        "ambiguous": 4,
        "no_answer": 4,
    }
    service = DataService(path)
    try:
        report = evaluation.evaluate_data(service, queries)
        assert report["query_count"] == 30 and report["success_rate"] == 1
        assert report["cases"][0]["payload_bytes"] > 0
        with pytest.raises(ValueError):
            evaluation.evaluate_data(service, [])
        wrong = dict(queries[0], expected_ids=[])
        assert evaluation.evaluate_data(service, [wrong])["success_rate"] == 0
    finally:
        service.close()
    assert evaluation.resolve_arguments(
        {"literal": 1, "id": "$0.results.0.id"}, [{"results": [{"id": "sample"}]}]
    ) == {"literal": 1, "id": "sample"}


@pytest.mark.parametrize("source", ["docs", "data"])
def test_evaluation_cli_and_entrypoint(tmp_path, source, monkeypatch, capsys):
    queries = ROOT / f"config/mcps/{source}-queries.json"
    if source == "docs":
        manifest = Manifest.model_validate_json(
            (ROOT / "config/mcps/docs-manifest.json").read_text()
        )
        artifact = tmp_path / "corpus.json"
        artifact.write_text(build_corpus(ROOT, manifest).model_dump_json())
    else:
        artifact = tmp_path / "gaia-mcp-synthetic-evaluation.sqlite"
        seed_database(artifact, "gaia-v1")
    output = tmp_path / "results" / "report.json"
    args = [source, "--artifact", str(artifact), "--queries", str(queries), "--output", str(output)]
    evaluation.main(args)
    assert json.loads(capsys.readouterr().out)["success_rate"] == 1
    assert json.loads(output.read_text())["success_rate"] == 1
    monkeypatch.setattr(sys, "argv", ["evaluation", *args])
    monkeypatch.delitem(sys.modules, "app.modules.wiki.mcps.evaluation", raising=False)
    runpy.run_module("app.modules.wiki.mcps.evaluation", run_name="__main__")
    assert json.loads(capsys.readouterr().out)["success_rate"] == 1
