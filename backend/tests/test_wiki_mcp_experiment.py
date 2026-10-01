import asyncio
import json
import runpy
import socket
import threading
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
import uvicorn
from openai.types.chat import ChatCompletionMessage
from starlette.middleware.base import BaseHTTPMiddleware
from test_wiki_mcp_integration import SECRET, corpus_files

from app.modules.wiki.mcps import experiment_cli
from app.modules.wiki.mcps.client import WikiMCPClient
from app.modules.wiki.mcps.context import CallContext
from app.modules.wiki.mcps.data.database import seed_database
from app.modules.wiki.mcps.data.service import DataService
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
from app.modules.wiki.mcps.experiment_scoring import score_answer
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
    records = asyncio.run(run_comparison(cases, corpus, None, None, config, path))
    assert [row["status"] for row in records] == ["failed", "completed", "completed"]
    assert records[0]["error_type"] == "TimeoutError" and "secret" not in path.read_text()
    assert asyncio.run(run_comparison(cases, corpus, None, None, config, path)) == records
    assert executor.await_count == 3
    executor.side_effect = TimeoutError()
    path = tmp_path / "failed.jsonl"
    assert len(asyncio.run(run_comparison(cases, corpus, None, None, config, path))) == 4
    assert len(asyncio.run(run_comparison(cases, corpus, None, None, config, path))) == 4
    executor.side_effect = [KeyboardInterrupt()]
    with pytest.raises(KeyboardInterrupt):
        asyncio.run(
            run_comparison(cases, corpus, None, None, config, tmp_path / "interrupted.jsonl")
        )


def test_cli_plan_live_and_cleanup(service, tmp_path, monkeypatch, capsys):
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
    assert asyncio.run(experiment_cli.live([], None, None, tmp_path)) == []
    assert runner.call_args.args[2] == "data-only"
    with pytest.raises(SystemExit):
        experiment_cli.main([*arguments, "--docs", "real-documents"])


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
