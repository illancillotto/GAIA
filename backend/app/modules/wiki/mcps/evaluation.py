"""Offline source evaluation with explicit ground truth and latency percentiles."""

import argparse
import json
import math
from pathlib import Path
from time import perf_counter

from .context import CallContext
from .data.service import DataService
from .docs.corpus import load_corpus
from .docs.service import DocsService


def percentiles(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        f"p{percentile}": ordered[max(0, math.ceil(len(ordered) * percentile / 100) - 1)]
        for percentile in (50, 95, 99)
    }


def _relevant_doc_ranks(results: list[dict], target: str | None, section: str) -> list[int]:
    return [
        index + 1
        for index, row in enumerate(results)
        if row["source_path"] == target and section in (row["section"] or "").casefold()
    ]


def evaluate_docs(service: DocsService, queries: list[dict]) -> dict:
    if not queries:
        raise ValueError("A nonempty reviewed documentation query set is required")
    cases, durations, scores, reciprocal_ranks, precision = [], [], [], [], []
    for query in queries:
        started = perf_counter()
        response = service.call("search_docs", {"query": query["query"], "limit": 10})
        durations.append(round((perf_counter() - started) * 1000, 3))
        target = query.get("expected_source_path")
        section = query.get("expected_section_contains", "").casefold()
        relevant = _relevant_doc_ranks(response["results"], target, section)
        passed = bool(relevant) if target else not response["results"]
        scores.append(int(passed))
        if target:
            reciprocal_ranks.append(1 / relevant[0] if relevant else 0)
            precision.append(len(relevant) / max(1, response["result_count"]))
        cases.append(
            {
                "id": query["id"],
                "passed": passed,
                "rank": relevant[0] if relevant else None,
                "result_count": response["result_count"],
                "estimated_tokens": response["estimated_tokens"],
            }
        )
    return {
        "source": "gaia_docs",
        "corpus_version": service.corpus.corpus_version,
        "query_count": len(queries),
        "success_rate": sum(scores) / len(scores),
        "recall_at_10": sum(rank > 0 for rank in reciprocal_ranks) / max(1, len(reciprocal_ranks)),
        "mrr": sum(reciprocal_ranks) / max(1, len(reciprocal_ranks)),
        "precision_at_10": sum(precision) / max(1, len(precision)),
        "latency_ms": percentiles(durations),
        "cases": cases,
    }


def resolve_arguments(arguments: dict, responses: list[dict]) -> dict:
    resolved = {}
    for key, value in arguments.items():
        if isinstance(value, str) and value.startswith("$"):
            reference = value[1:].split(".")
            value = responses[int(reference[0])]
            for component in reference[1:]:
                value = value[int(component)] if isinstance(value, list) else value[component]
        resolved[key] = value
    return resolved


def evaluate_data(service: DataService, queries: list[dict]) -> dict:
    if not queries:
        raise ValueError("A nonempty reviewed structured query set is required")
    cases, durations = [], []
    context = CallContext(
        principal="offline-evaluation",
        scopes=frozenset({"utenze.read", "catasto.read", "ruolo.read"}),
    )
    for query in queries:
        responses = []
        started = perf_counter()
        for step in query["steps"]:
            response = service.call(
                step["tool"], resolve_arguments(step["arguments"], responses), context
            )
            responses.append(response)
        durations.append(round((perf_counter() - started) * 1000, 3))
        final = responses[-1]
        ids = sorted(record["id"] for record in final["results"])
        passed = ids == sorted(query["expected_ids"]) and "error" not in final
        cases.append(
            {
                "id": query["id"],
                "category": query["category"],
                "passed": passed,
                "tool_calls": len(responses),
                "result_count": final["result_count"],
                "payload_bytes": len(json.dumps(responses, ensure_ascii=False).encode()),
                "estimated_tokens": sum(response["estimated_tokens"] for response in responses),
            }
        )
    return {
        "source": "gaia_synthetic_db",
        "dataset_version": service.manifest["dataset_version"],
        "query_count": len(queries),
        "success_rate": sum(case["passed"] for case in cases) / len(cases),
        "latency_ms": percentiles(durations),
        "cases": cases,
    }


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Offline GAIA MCP source evaluation")
    parser.add_argument("source", choices=["docs", "data"])
    parser.add_argument("--artifact", type=Path, required=True)
    parser.add_argument("--queries", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    queries = json.loads(args.queries.read_text())
    service = (
        DocsService(load_corpus(args.artifact))
        if args.source == "docs"
        else DataService(args.artifact)
    )
    try:
        report = (
            evaluate_docs(service, queries)
            if args.source == "docs"
            else evaluate_data(service, queries)
        )
    finally:
        service.close()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "cases"}))


if __name__ == "__main__":
    main()
