import asyncio
import fcntl
import json
import runpy
import socket
import threading
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import NAMESPACE_URL, uuid5

import pytest
import uvicorn
from openai.types.chat import ChatCompletionMessage
from starlette.middleware.base import BaseHTTPMiddleware
from test_wiki_mcp_integration import SECRET, corpus_files

from app.modules.wiki.mcps import experiment_cli
from app.modules.wiki.mcps.agent import WikiMCPAgent
from app.modules.wiki.mcps.client import WikiMCPClient
from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.data import database as synthetic_database
from app.modules.wiki.mcps.data.database import seed_database
from app.modules.wiki.mcps.data.generator import generate_dataset
from app.modules.wiki.mcps.data.inputs import INPUTS
from app.modules.wiki.mcps.data.service import DataService, serialize_record
from app.modules.wiki.mcps.docs.corpus import load_corpus
from app.modules.wiki.mcps.docs.service import DocsService
from app.modules.wiki.mcps.experiment_cases import ExperimentCase, synthetic_cases
from app.modules.wiki.mcps.experiment_runner import (
    ComparisonExecutor,
    ExperimentConfig,
    ResultJournal,
    TracedModel,
    VerifiedDataSources,
    experiment_manifest,
    run_comparison,
    schedule,
)
from app.modules.wiki.mcps.experiment_scoring import score_answer, verified_absence
from app.modules.wiki.mcps.experiment_static import EXPERIMENT_SCOPES, SyntheticStaticCorpus
from app.modules.wiki.mcps.http import create_http_app


@pytest.fixture
def service(tmp_path):
    path = tmp_path / "gaia-mcp-synthetic-experiment.sqlite"
    seed_database(path, "experiment-tests")
    service = DataService(path)
    yield service
    service.close()


@pytest.fixture
def context():
    return CallContext(principal="synthetic-test", scopes=EXPERIMENT_SCOPES)


@pytest.fixture
def corpus(service, context):
    corpus = SyntheticStaticCorpus(service, context)
    yield corpus
    corpus.close()


def completion(answer="", tools=None):
    message = ChatCompletionMessage(role="assistant", content=answer, tool_calls=tools)
    return SimpleNamespace(choices=[SimpleNamespace(message=message)])


def model_stub(callback):
    return SimpleNamespace(
        chat=SimpleNamespace(completions=SimpleNamespace(create=AsyncMock(side_effect=callback)))
    )


def tool_call(name, arguments):
    return {
        "id": "call-synthetic",
        "type": "function",
        "function": {"name": name, "arguments": json.dumps(arguments)},
    }


def answer_for(case):
    return json.dumps(
        {
            "status": "found" if case.expected else "absent",
            "records": case.expected,
            "citations": [{"entity": case.entity, "record_id": row["id"]} for row in case.expected],
        }
    )


def evidence_for(case):
    return [
        {
            "results": case.expected,
            "result_count": len(case.expected),
            "provenance": [
                {"source": "gaia_synthetic_db", "entity": case.entity, "record_id": row["id"]}
                for row in case.expected
            ],
        }
    ]


def test_generated_cases_and_static_corpus_are_dataset_only(service, corpus, context):
    cases = synthetic_cases(service)
    assert len(cases) == 5 and cases[-1].expected == []
    assert cases[-2].entity == "payments" and cases[-2].expected
    for case in cases:
        assert "expected" not in case.question and "sintetico" in case.question
    case = cases[0]
    result = corpus.retrieve(case.expected[0]["id"], 6000)
    assert case.expected[0] in result["results"]
    assert result["provenance"][0]["dataset_version"] == corpus.version
    assert all(row["source"] == "gaia_synthetic_db" for row in result["provenance"])
    assert corpus.retrieve("", 100)["result_count"] == 0
    assert corpus.retrieve("SYN-ABSENT-UNIQUE", 100)["result_count"] == 0
    assert corpus.retrieve("synthetic_identifier", 100)["result_count"] == 0
    assert corpus.retrieve("synthetic_identifier", 6000)["truncated"] is True
    with pytest.raises(PermissionError):
        SyntheticStaticCorpus(service, replace(context, scopes=frozenset({"docs.read"})))
    for count in (0, 11):
        with pytest.raises(ValueError):
            synthetic_cases(service, count)


@pytest.mark.parametrize(
    "changes",
    [
        {"repeats": 0},
        {"repeats": 11},
        {"max_attempts": 0},
        {"max_attempts": 4},
        {"max_calls": 0},
        {"max_calls": 17},
        {"evidence_tokens": 99},
        {"evidence_tokens": 12001},
    ],
)
def test_invalid_experiment_limits(changes):
    with pytest.raises(ValueError):
        ExperimentConfig(**changes)


def test_schedule_reproducibility_and_manifest_binding(service):
    cases = synthetic_cases(service)
    config = ExperimentConfig()
    first = schedule(cases, config)
    assert first == schedule(cases, config) and len(first) == 20
    assert first != schedule(cases, replace(config, seed=43))
    manifest = experiment_manifest(cases, "version", config)
    assert manifest == experiment_manifest(cases, "version", config)
    assert manifest != experiment_manifest(cases, "new-version", config)
    assert manifest != experiment_manifest(cases, "version", replace(config, max_calls=7))
    for invalid in ([], [*cases, cases[0]]):
        with pytest.raises(ValueError):
            experiment_manifest(invalid, "version", config)


@pytest.mark.parametrize(
    "answer", ["not JSON", "[]", "{}", '{"status":"other","records":[],"citations":[]}']
)
def test_malformed_answer_is_not_scored_as_success(answer):
    assert score_answer(ExperimentCase("empty", "synthetic", "subjects", []), answer, []) == {
        "passed": False,
        "error": "INVALID_ANSWER",
    }


def test_facts_citations_duplicates_and_no_answer_scoring(service):
    case = synthetic_cases(service)[0]
    evidence = evidence_for(case)
    assert score_answer(case, answer_for(case), evidence)["passed"]
    payload = json.loads(answer_for(case))
    payload["records"][0]["id"] = []
    assert score_answer(case, json.dumps(payload), evidence)["error"] == "INVALID_ANSWER"
    payload = json.loads(answer_for(case))
    payload["records"][0]["invented_field"] = "synthetic hallucination"
    assert not score_answer(case, json.dumps(payload), evidence)["passed"]
    payload = json.loads(answer_for(case))
    payload["citations"].append(payload["citations"][0])
    assert not score_answer(case, json.dumps(payload), evidence)["passed"]
    payload = json.loads(answer_for(case))
    payload["records"][0]["display_name"] = "invented"
    score = score_answer(case, json.dumps(payload), evidence)
    assert not score["passed"] and score["fact_accuracy"] < 1
    payload = json.loads(answer_for(case))
    payload["records"].append(payload["records"][0])
    assert not score_answer(case, json.dumps(payload), evidence)["identity_match"]
    payload["records"] = []
    assert not score_answer(case, json.dumps(payload), evidence)["passed"]
    payload = json.loads(answer_for(case))
    payload["citations"][0]["entity"] = "docs"
    assert not score_answer(case, json.dumps(payload), evidence)["citation_valid"]
    evidence[0]["provenance"][0]["source"] = "real-docs"
    assert not score_answer(case, answer_for(case), evidence)["passed"]
    empty = synthetic_cases(service)[-1]
    empty_evidence = evidence_for(empty)
    assert score_answer(empty, answer_for(empty), empty_evidence)["no_answer_valid"]
    assert not score_answer(empty, answer_for(empty), [])["passed"]
    empty_evidence[0]["error"] = {"code": "FORBIDDEN"}
    assert not score_answer(empty, answer_for(empty), empty_evidence)["passed"]
    assert not score_answer(empty, answer_for(empty), evidence_for(case))["passed"]
    assert not score_answer(case, answer_for(empty), evidence_for(case))["passed"]


def test_journal_append_resume_lock_and_corruption(tmp_path):
    path = tmp_path / "results.jsonl"
    manifest = {"experiment_id": "synthetic"}
    first = ResultJournal(path, manifest)
    first.append({"item": {}, "status": "failed"})
    with pytest.raises(BlockingIOError):
        ResultJournal(path, manifest)
    first.close()
    second = ResultJournal(path, manifest)
    assert second.records == [{"item": {}, "status": "failed"}]
    second.close()
    with pytest.raises(ValueError, match="different experiment"):
        ResultJournal(path, {})
    before = path.read_bytes()
    path.write_bytes(before + b'{"incomplete":true}')
    with pytest.raises(ValueError, match="Incomplete"):
        ResultJournal(path, manifest)
    assert path.read_bytes() == before + b'{"incomplete":true}'
    path.write_text("invalid\n")
    with pytest.raises(ValueError):
        ResultJournal(path, manifest)


@pytest.mark.parametrize(
    ("content", "error_message"),
    [
        ('{"manifest": {"experiment_id": "same"}}', "Incomplete"),
        ('invalid\n{"incomplete":true}', "Incomplete"),
        ("invalid\n", "Expecting value"),
        ('{"manifest": {"experiment_id": "other"}}\n', "different experiment"),
    ],
)
def test_journal_validation_failure_preserves_bytes_and_releases_lock(
    tmp_path, content, error_message
):
    path = tmp_path / "rejected.jsonl"
    path.write_text(content)
    original = path.read_bytes()

    with pytest.raises(ValueError, match=error_message):
        ResultJournal(path, {"experiment_id": "same"})

    assert path.read_bytes() == original
    with path.open("a+") as reopened:
        fcntl.flock(reopened, fcntl.LOCK_EX | fcntl.LOCK_NB)


def test_journal_initial_write_failure_closes_file_and_releases_lock(tmp_path, monkeypatch):
    path = tmp_path / "unavailable.jsonl"
    manifest = {"experiment_id": "same"}
    attempted = []
    original_append = ResultJournal.append

    def unavailable_append(self, row):
        attempted.append((self, row))
        raise OSError("Journal unavailable")

    monkeypatch.setattr(ResultJournal, "append", unavailable_append)
    with pytest.raises(OSError, match="Journal unavailable"):
        ResultJournal(path, manifest)

    journal, row = attempted[0]
    assert row == {"manifest": manifest}
    assert journal.file.closed
    assert path.read_bytes() == b""
    monkeypatch.setattr(ResultJournal, "append", original_append)
    reopened = ResultJournal(path, manifest)
    try:
        assert reopened.records == []
        assert json.loads(path.read_text()) == {"manifest": manifest}
    finally:
        reopened.close()


def test_verified_sources_reject_docs_before_invocation_and_wrong_dataset(context):
    sources = SimpleNamespace(
        list_tools=AsyncMock(return_value=[{"name": "data__get_subject"}]),
        call_tool=AsyncMock(
            return_value={"source": "gaia_synthetic_db", "dataset_version": "same"}
        ),
    )
    verified = VerifiedDataSources(sources, "same")
    assert asyncio.run(verified.list_tools(context)) == [{"name": "data__get_subject"}]
    assert (
        asyncio.run(verified.call_tool("data__get_subject", {}, context))["dataset_version"]
        == "same"
    )
    sources.list_tools.return_value = [{"name": "search_docs"}]
    with pytest.raises(ValueError):
        asyncio.run(verified.list_tools(context))
    sources.call_tool.reset_mock()
    with pytest.raises(PermissionError):
        asyncio.run(verified.call_tool("search_docs", {}, context))
    sources.call_tool.assert_not_called()
    for response in (
        {"source": "gaia_docs", "dataset_version": "same"},
        {"source": "gaia_synthetic_db", "dataset_version": "other"},
    ):
        sources.call_tool.return_value = response
        with pytest.raises(PermissionError):
            asyncio.run(verified.call_tool("data__get_subject", {}, context))


def test_existing_agent_trace_and_static_contract(service, corpus, context):
    case = synthetic_cases(service)[0]
    sources = SimpleNamespace(
        list_tools=AsyncMock(
            return_value=[
                {
                    "name": "data__get_subject",
                    "description": "synthetic",
                    "input_schema": {"type": "object"},
                }
            ]
        ),
        call_tool=AsyncMock(
            side_effect=lambda name, arguments, context: service.call(
                name.removeprefix("data__"), arguments, context
            )
        ),
    )
    answers = [
        completion(tools=[tool_call("data__get_subject", {"subject_id": case.expected[0]["id"]})]),
        completion(answer_for(case)),
    ]
    model = model_stub(lambda **arguments: answers.pop(0))
    result = asyncio.run(
        ComparisonExecutor(sources, model, corpus, ExperimentConfig()).execute(case, "mcp", context)
    )
    assert result["score"]["passed"] and result["tool_calls"] == 1
    assert len(result["evidence"]) == 1
    assert "docs" not in json.dumps(model.chat.completions.create.call_args.kwargs["tools"])
    model = model_stub(lambda **arguments: completion(answer_for(case)))
    result = asyncio.run(
        ComparisonExecutor(sources, model, corpus, ExperimentConfig()).execute(
            case, "static", context
        )
    )
    assert result["score"]["passed"] and result["tool_calls"] == 0
    assert "tools" not in model.chat.completions.create.call_args.kwargs
    assert "expected" not in json.dumps(result["messages"])
    model = model_stub(lambda **arguments: completion())
    assert not asyncio.run(
        ComparisonExecutor(sources, model, corpus, ExperimentConfig()).execute(
            case, "static", context
        )
    )["score"]["passed"]
    model = model_stub(lambda **arguments: completion(tools=[tool_call("search_docs", {})]))
    with pytest.raises(RuntimeError):
        asyncio.run(
            ComparisonExecutor(sources, model, corpus, ExperimentConfig()).execute(
                case, "static", context
            )
        )
    traced = TracedModel(model)
    assert traced.evidence() == []


def test_paired_runner_retry_resume_and_exhaustion(service, corpus, tmp_path, monkeypatch):
    cases = synthetic_cases(service)[:1]
    executor = AsyncMock(
        side_effect=[
            TimeoutError("secret never recorded"),
            {"score": {"passed": True}},
            {"score": {"passed": False}},
        ]
    )
    monkeypatch.setattr(ComparisonExecutor, "execute", executor)
    config = ExperimentConfig(repeats=1)
    path = tmp_path / "results.jsonl"
    comparison = ComparisonExecutor(None, None, corpus, config)
    records = asyncio.run(run_comparison(cases, comparison, path))
    assert [row["status"] for row in records] == ["failed", "completed", "completed"]
    assert records[0]["error_type"] == "TimeoutError" and "secret" not in path.read_text()
    assert asyncio.run(run_comparison(cases, comparison, path)) == records
    assert executor.await_count == 3
    executor.side_effect = TimeoutError()
    path = tmp_path / "failed.jsonl"
    assert len(asyncio.run(run_comparison(cases, comparison, path))) == 4
    assert len(asyncio.run(run_comparison(cases, comparison, path))) == 4
    executor.side_effect = [KeyboardInterrupt()]
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(run_comparison(cases, comparison, tmp_path / "interrupted.jsonl"))


def test_paired_runner_partial_resume_preserves_attempts_and_context(
    service, corpus, tmp_path, monkeypatch
):
    cases = synthetic_cases(service)[:1]
    config = ExperimentConfig(repeats=1, max_attempts=3)
    manifest = experiment_manifest(cases, corpus.version, config)
    pending, completed = schedule(cases, config)
    path = tmp_path / "partial.jsonl"
    previous = [
        {"item": pending, "attempt": 1, "status": "failed"},
        {"item": completed, "attempt": 1, "status": "completed"},
    ]
    journal = ResultJournal(path, manifest)
    for row in previous:
        journal.append(row)
    journal.close()
    executor = AsyncMock(side_effect=[TimeoutError(), {"score": {"passed": True}}])
    monkeypatch.setattr(ComparisonExecutor, "execute", executor)

    comparison = ComparisonExecutor(None, None, corpus, config)
    records = asyncio.run(run_comparison(cases, comparison, path))

    assert records[:2] == previous
    assert [(row["attempt"], row["status"]) for row in records[2:]] == [
        (2, "failed"),
        (3, "completed"),
    ]
    assert [json.loads(line) for line in path.read_text().splitlines()][1:] == records
    assert executor.await_count == 2
    first_call, retry_call = executor.await_args_list
    assert first_call.args[:2] == (cases[0], pending["condition"])
    assert first_call.args[2] is retry_call.args[2]
    resumed_context = first_call.args[2]
    assert resumed_context.principal == "synthetic-comparison"
    assert resumed_context.scopes == EXPERIMENT_SCOPES
    assert resumed_context.experiment_run_id == str(
        uuid5(
            NAMESPACE_URL,
            manifest["experiment_id"]
            + json.dumps(pending, sort_keys=True, separators=(",", ":"), ensure_ascii=False),
        )
    )
    assert asyncio.run(run_comparison(cases, comparison, path)) == records
    assert executor.await_count == 2


@pytest.mark.parametrize("failure", ["cancelled", "journal-write"])
def test_paired_runner_releases_journal_on_abort(service, corpus, tmp_path, monkeypatch, failure):
    cases = synthetic_cases(service)[:1]
    config = ExperimentConfig(repeats=1)
    manifest = experiment_manifest(cases, corpus.version, config)
    path = tmp_path / "aborted.jsonl"
    executor = AsyncMock(return_value={"score": {"passed": True}})
    monkeypatch.setattr(ComparisonExecutor, "execute", executor)
    error = asyncio.CancelledError if failure == "cancelled" else OSError
    if failure == "cancelled":
        executor.side_effect = asyncio.CancelledError()
    else:
        original_append = ResultJournal.append

        def unavailable_append(self, row):
            if "item" in row:
                raise OSError("Journal unavailable")
            original_append(self, row)

        monkeypatch.setattr(ResultJournal, "append", unavailable_append)

    with pytest.raises(error):
        asyncio.run(run_comparison(cases, ComparisonExecutor(None, None, corpus, config), path))

    reopened = ResultJournal(path, manifest)
    try:
        assert reopened.manifest == manifest
        assert reopened.records == []
    finally:
        reopened.close()
    assert executor.await_count == 1


def test_cli_live_failure_closes_model(tmp_path, monkeypatch):
    model = Mock()
    model.__aenter__ = AsyncMock(return_value=model)
    model.__aexit__ = AsyncMock(return_value=False)
    monkeypatch.setattr(experiment_cli, "model_client", lambda: model)
    monkeypatch.setattr(experiment_cli, "source_client", lambda: "data-only")
    runner = AsyncMock(side_effect=OSError("Journal unavailable"))
    monkeypatch.setattr(experiment_cli, "run_comparison", runner)

    with pytest.raises(OSError, match="Journal unavailable"):
        asyncio.run(experiment_cli.live([], None, None, tmp_path / "failed.jsonl"))

    runner.assert_awaited_once()
    model.__aenter__.assert_awaited_once()
    model.__aexit__.assert_awaited_once()
    assert model.__aexit__.await_args.args[0] is OSError


def test_cli_plan_live_and_cleanup(service, corpus, tmp_path, monkeypatch, capsys):
    path = tmp_path / "gaia-mcp-synthetic-cli.sqlite"
    seed_database(path, "cli-tests")
    arguments = ["--database", str(path), "--output", str(tmp_path / "output.jsonl")]
    experiment_cli.main(arguments)
    plan = json.loads(capsys.readouterr().out)
    assert plan["manifest"]["model"] == "gpt-reserve" and len(plan["schedule"]) == 20
    assert not (tmp_path / "output.jsonl").exists()
    original_live = experiment_cli.live
    monkeypatch.setattr(
        experiment_cli,
        "live",
        AsyncMock(return_value=[{"status": "completed"}, {"status": "failed"}]),
    )
    experiment_cli.main([*arguments, "--live"])
    monkeypatch.setattr(experiment_cli, "live", original_live)
    assert "Completed: 1; attempts: 2" in capsys.readouterr().out
    monkeypatch.setattr("sys.argv", ["experiment_cli", *arguments])
    with pytest.warns(RuntimeWarning, match="found in sys.modules"):
        runpy.run_module("app.modules.wiki.mcps.experiment_cli", run_name="__main__")
    model = Mock()
    model.__aenter__ = AsyncMock(return_value=model)
    model.__aexit__ = AsyncMock()
    monkeypatch.setattr(experiment_cli, "model_client", lambda: model)
    monkeypatch.setattr(experiment_cli, "source_client", lambda: "data-only")
    runner = AsyncMock(return_value=[])
    monkeypatch.setattr(experiment_cli, "run_comparison", runner)
    cases = synthetic_cases(service)[:1]
    config = ExperimentConfig(repeats=1, max_attempts=3)
    assert asyncio.run(experiment_cli.live(cases, corpus, config, tmp_path)) == []
    passed_cases, passed_executor, passed_output = runner.call_args.args
    assert passed_cases is cases and passed_output == tmp_path
    assert passed_executor.sources == "data-only"
    assert passed_executor.model is model
    assert passed_executor.corpus is corpus
    assert passed_executor.config is config
    model.__aexit__.assert_awaited_once()
    with pytest.raises(SystemExit):
        experiment_cli.main([*arguments, "--docs", "real-documents"])


@pytest.fixture
def multiple_payments_service(tmp_path, monkeypatch):
    dataset = generate_dataset("synthetic-pagination-test-v1")
    original = dataset["payments"][0]
    total = original["amount_cents"]
    original["amount_cents"] = total // 3
    for index in (1, 2):
        dataset["payments"].append(
            {
                **original,
                "id": str(uuid5(NAMESPACE_URL, f"synthetic-payment-page-{index}")),
                "amount_cents": total // 3 if index == 1 else total - 2 * (total // 3),
            }
        )
    monkeypatch.setattr(synthetic_database, "generate_dataset", lambda seed: dataset)
    path = tmp_path / "gaia-mcp-synthetic-multiple-payments.sqlite"
    seed_database(path, "synthetic-pagination-test-v1")
    service = DataService(path)
    yield service, original["notice_id"]
    service.close()


def data_sources(service):
    return SimpleNamespace(
        list_tools=AsyncMock(
            return_value=[
                {
                    "name": f"data__{name}",
                    "description": "Synthetic data",
                    "input_schema": model.model_json_schema(),
                }
                for name, model in INPUTS.items()
            ]
        ),
        call_tool=AsyncMock(
            side_effect=lambda name, arguments, context: service.call(
                name.removeprefix("data__"), arguments, context
            )
        ),
    )


def test_agent_multiple_payments_follows_real_cursors(multiple_payments_service, context):
    service, notice_id = multiple_payments_service
    notice = service.connection.execute(
        "SELECT * FROM role_notices WHERE id=?", (notice_id,)
    ).fetchone()
    expected = [
        serialize_record(row)
        for row in service.connection.execute(
            "SELECT * FROM payments WHERE notice_id=? ORDER BY id", (notice_id,)
        )
    ]
    case = ExperimentCase(
        "paginated", "Restituisci tutti i pagamenti sintetici", "payments", expected
    )
    sources = data_sources(service)

    async def decide(**arguments):
        tools = [
            json.loads(message["content"])
            for message in arguments["messages"]
            if message["role"] == "tool"
        ]
        if not tools:
            return completion(
                tools=[
                    tool_call("data__search_role_notices", {"notice_code": notice["notice_code"]})
                ]
            )
        if tools[-1]["tool"] == "search_role_notices":
            return completion(
                tools=[
                    tool_call(
                        "data__get_payments_by_notice",
                        {"notice_id": tools[-1]["results"][0]["id"], "limit": 1},
                    )
                ]
            )
        if tools[-1]["next_cursor"]:
            return completion(
                tools=[
                    tool_call(
                        "data__get_payments_by_notice",
                        {"notice_id": notice_id, "limit": 1, "cursor": tools[-1]["next_cursor"]},
                    )
                ]
            )
        records = [row for response in tools[1:] for row in response["results"]]
        return completion(answer_for(replace(case, expected=records)))

    model = model_stub(decide)
    traced = TracedModel(model)
    result = asyncio.run(
        WikiMCPAgent(sources, traced, "gpt-reserve").answer(case.question, context)
    )
    assert score_answer(case, result["answer"], traced.evidence())["passed"]
    assert result["tool_calls"] == 4 and len(json.loads(result["answer"])["records"]) == 3
    assert [response["truncated"] for response in traced.evidence()[1:]] == [True, True, False]
    assert (
        len(
            {
                source["record_id"]
                for source in result["provenance"]
                if source["entity"] == "payments"
            }
        )
        == 3
    )


@pytest.mark.parametrize("corruption", ["segment-copy", "other-payment"])
def test_model_payment_citation_corruption_is_preserved_and_rejected(
    multiple_payments_service, context, corruption
):
    service, notice_id = multiple_payments_service
    response = service.call("get_payments_by_notice", {"notice_id": notice_id}, context)
    case = ExperimentCase(
        "citation-regression", "Pagamenti sintetici", "payments", response["results"]
    )
    payload = json.loads(answer_for(case))
    original_id = payload["citations"][0]["record_id"]
    other_id = payload["citations"][1]["record_id"]
    segments = original_id.split("-")
    segments[2] = other_id.split("-")[2]
    segments[3] = other_id.split("-")[3]
    corrupted_id = "-".join(segments) if corruption == "segment-copy" else other_id
    assert corrupted_id != original_id
    payload["citations"][0]["record_id"] = corrupted_id
    raw_answer = json.dumps(payload)

    async def decide(**arguments):
        if any(message["role"] == "tool" for message in arguments["messages"]):
            return completion(raw_answer)
        return completion(
            tools=[tool_call("data__get_payments_by_notice", {"notice_id": notice_id})]
        )

    traced = TracedModel(model_stub(decide))
    result = asyncio.run(
        WikiMCPAgent(data_sources(service), traced, "gpt-reserve").answer(case.question, context)
    )
    assert result["answer"] == raw_answer
    assert traced.evidence()[0]["results"] == case.expected
    assert original_id in {source["record_id"] for source in result["provenance"]}
    score = score_answer(case, result["answer"], traced.evidence())
    assert score["identity_match"] and score["facts_match"] and score["fields_match"]
    assert not score["citation_valid"] and not score["passed"]
    assert json.loads(result["answer"])["citations"][0]["record_id"] == corrupted_id


def test_no_payments_scoring_requires_terminal_entity(service, context):
    notice = service.connection.execute(
        "SELECT * FROM role_notices WHERE id NOT IN (SELECT notice_id FROM payments) ORDER BY id LIMIT 1"
    ).fetchone()
    parent = service.call("search_role_notices", {"notice_code": notice["notice_code"]}, context)
    empty = service.call(
        "get_payments_by_notice", {"notice_id": parent["results"][0]["id"]}, context
    )
    case = ExperimentCase("no-payments", "Pagamenti dell'avviso sintetico", "payments", [])
    assert score_answer(case, answer_for(case), [parent, empty])["passed"]
    assert not verified_absence("payments", [parent])
    assert verified_absence("payments", [{"tool": "search_role_notices", "result_count": 0}])
    assert not verified_absence("payments", [{"tool": "search_subjects", "result_count": 0}])
    assert not verified_absence("payments", [parent, {"result_count": 0}])
    for change in (
        {"truncated": True},
        {"next_cursor": "synthetic-cursor"},
        {"error": {"code": "PERMISSION_DENIED"}},
    ):
        assert not score_answer(case, answer_for(case), [parent, {**empty, **change}])["passed"]
    assert not verified_absence("payments", [{"error": {"code": "INVALID_ARGUMENT"}}, empty])
    assert verified_absence("payments", [{"result_count": 0}])
    invalid_status = json.loads(answer_for(case))
    invalid_status["status"] = "found"
    assert not score_answer(case, json.dumps(invalid_status), [parent, empty])["passed"]
    cited_parent = json.loads(answer_for(case))
    cited_parent["citations"] = [{"entity": "role_notices", "record_id": notice["id"]}]
    assert not score_answer(case, json.dumps(cited_parent), [parent, empty])["citation_valid"]


@pytest.mark.parametrize("budget", ["permissions", "calls", "tokens"])
def test_agent_denial_and_exhaustion_do_not_become_valid_absence(service, context, budget):
    case = synthetic_cases(service)[-2]
    notice_id = case.expected[0]["notice_id"]
    notice = service.connection.execute(
        "SELECT * FROM role_notices WHERE id=?", (notice_id,)
    ).fetchone()
    sources = data_sources(service)
    if budget == "permissions":
        context = replace(context, scopes=frozenset({"utenze.read"}))
    model = model_stub(
        lambda **arguments: (
            completion(answer_for(replace(case, expected=[])))
            if any(message["role"] == "tool" for message in arguments["messages"])
            else completion(
                tools=[
                    tool_call("data__search_role_notices", {"notice_code": notice["notice_code"]})
                ]
            )
        )
    )
    traced = TracedModel(model)
    agent = WikiMCPAgent(
        sources,
        traced,
        "gpt-reserve",
        max_calls=1 if budget == "calls" else 8,
        max_evidence_tokens=100 if budget == "tokens" else 6000,
    )
    result = asyncio.run(agent.answer(case.question, context))
    assert not score_answer(case, result["answer"], traced.evidence())["passed"]
    assert not score_answer(replace(case, expected=[]), result["answer"], traced.evidence())[
        "passed"
    ]
    if budget == "permissions":
        assert traced.evidence()[0]["error"]["code"] == "PERMISSION_DENIED"
    else:
        assert model.chat.completions.create.call_args.kwargs["tool_choice"] == "none"
    assert result["tool_calls"] == 1


def test_comparison_uses_real_sdk_catalog_and_http_tools_without_docs(tmp_path, context):
    docs_path, database = corpus_files(tmp_path)
    data = DataService(database)
    docs = DocsService(load_corpus(docs_path))
    corpus = SyntheticStaticCorpus(data, context)
    application = create_http_app(docs, data, SECRET)
    paths = []

    async def record(request, call_next):
        paths.append(request.url.path)
        return await call_next(request)

    application.app.add_middleware(BaseHTTPMiddleware, dispatch=record)
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    server = uvicorn.Server(uvicorn.Config(application, log_level="error", access_log=False))
    thread = threading.Thread(
        target=lambda: asyncio.run(server.serve(sockets=[listener])), daemon=True
    )
    thread.start()

    async def exercise():
        for _attempt in range(200):
            if server.started:
                break
            await asyncio.sleep(0.01)
        assert server.started
        source = WikiMCPClient(None, f"http://127.0.0.1:{listener.getsockname()[1]}/data/", SECRET)
        case = synthetic_cases(data)[0]
        messages = [
            completion(
                tools=[tool_call("data__get_subject", {"subject_id": case.expected[0]["id"]})]
            ),
            completion(answer_for(case)),
        ]
        model = model_stub(lambda **arguments: messages.pop(0))
        result = await ComparisonExecutor(source, model, corpus, ExperimentConfig()).execute(
            case, "mcp", context
        )
        assert result["score"]["passed"] and result["tool_calls"] == 1
        payment_case = synthetic_cases(data)[-2]
        absent_case = replace(
            payment_case,
            id="notice-absent",
            expected=[],
            question="Trova l'avviso sintetico con codice SYN-N-NOT-EXISTENT e i suoi pagamenti.",
        )
        for case in [payment_case, absent_case]:
            if case.expected:
                notice = data.connection.execute(
                    "SELECT notice_code FROM role_notices WHERE id=?",
                    (case.expected[0]["notice_id"],),
                ).fetchone()
                messages = [
                    completion(
                        tools=[
                            tool_call(
                                "data__search_role_notices", {"notice_code": notice["notice_code"]}
                            )
                        ]
                    ),
                    completion(
                        tools=[
                            tool_call(
                                "data__get_payments_by_notice",
                                {"notice_id": case.expected[0]["notice_id"]},
                            )
                        ]
                    ),
                    completion(answer_for(case)),
                ]
            else:
                messages = [
                    completion(
                        tools=[
                            tool_call(
                                "data__search_role_notices", {"notice_code": "SYN-N-NOT-EXISTENT"}
                            )
                        ]
                    ),
                    completion(answer_for(case)),
                ]
            model = model_stub(
                lambda completion_queue=messages, **arguments: completion_queue.pop(0)
            )
            result = await ComparisonExecutor(source, model, corpus, ExperimentConfig()).execute(
                case, "mcp", context
            )
            assert result["score"]["passed"]
            assert result["tool_calls"] == (2 if case.expected else 1)
        catalog = await source.list_tools(context)
        notice_tool = next(tool for tool in catalog if tool["name"] == "data__search_role_notices")
        assert "notice_code" in notice_tool["input_schema"]["properties"]
        assert "combined with AND" in notice_tool["description"]
        assert all(
            tool["function"]["name"].startswith("data__")
            for tool in model.chat.completions.create.call_args.kwargs["tools"]
        )
        assert paths and not any("docs" in path for path in paths)

    try:
        asyncio.run(exercise())
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        corpus.close()
        docs.close()
        data.close()
