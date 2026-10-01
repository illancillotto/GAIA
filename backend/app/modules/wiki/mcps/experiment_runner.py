"""Paired, resumable synthetic experiments using the existing Wiki agent."""

import fcntl
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from uuid import NAMESPACE_URL, uuid5

from .agent import SYSTEM_PROMPT, WikiMCPAgent
from .context import CallContext
from .data.queries import QUERIES
from .docs.corpus import canonical_json, digest, estimated_tokens
from .experiment_cases import ANSWER_CONTRACT, PROTOCOL, ExperimentCase
from .experiment_scoring import score_answer
from .experiment_static import EXPERIMENT_SCOPES, SyntheticStaticCorpus


@dataclass(frozen=True)
class ExperimentConfig:
    seed: int = 42
    repeats: int = 2
    max_attempts: int = 2
    max_calls: int = 8
    evidence_tokens: int = 6000

    def __post_init__(self):
        if not 1 <= self.repeats <= 10 or not 1 <= self.max_attempts <= 3:
            raise ValueError("Invalid repetition/retry limits")
        if not 1 <= self.max_calls <= 16 or not 100 <= self.evidence_tokens <= 12000:
            raise ValueError("Invalid experiment budget")


def experiment_manifest(
    cases: list[ExperimentCase], dataset_version: str, config: ExperimentConfig
) -> dict:
    if not cases or len({case.id for case in cases}) != len(cases):
        raise ValueError("Nonempty unique cases are required")
    sources = [
        "agent.py",
        "experiment_cases.py",
        "experiment_static.py",
        "experiment_scoring.py",
        "experiment_runner.py",
        "data/inputs.py",
        "data/queries.py",
        "data/server.py",
        "data/service.py",
        "client.py",
    ]
    manifest = {
        "protocol": PROTOCOL,
        "model": "gpt-reserve",
        "dataset_version": dataset_version,
        "config": asdict(config),
        "cases": [asdict(case) for case in cases],
        "code_hashes": {
            name: digest((Path(__file__).parent / name).read_bytes()) for name in sources
        },
    }
    manifest["experiment_id"] = digest(canonical_json(manifest).encode())
    return manifest


def schedule(cases: list[ExperimentCase], config: ExperimentConfig) -> list[dict]:
    items = [
        {"case_id": case.id, "condition": condition, "repeat": repeat}
        for repeat in range(config.repeats)
        for case in cases
        for condition in ("static", "mcp")
    ]
    random.Random(config.seed).shuffle(items)
    return items


class ResultJournal:
    def __init__(self, path: Path, manifest: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.file = path.open("a+", encoding="utf-8")
        try:
            fcntl.flock(self.file, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.file.seek(0)
            lines = list(self.file)
            if any(not line.endswith("\n") for line in lines):
                raise ValueError("Incomplete journal; preserve it for inspection")
            rows = [json.loads(line) for line in lines]
            if rows and rows[0] != {"manifest": manifest}:
                raise ValueError("Journal belongs to a different experiment")
            self.records = rows[1:]
            if not rows:
                self.append({"manifest": manifest})
        except Exception:
            self.file.close()
            raise

    def append(self, row: dict):
        self.file.write(canonical_json(row) + "\n")
        self.file.flush()
        import os

        os.fsync(self.file.fileno())

    def close(self):
        self.file.close()


class TracedModel:
    def __init__(self, client):
        self.client = client
        self.messages = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))

    async def create(self, **arguments):
        self.messages = json.loads(canonical_json(arguments["messages"]))
        return await self.client.chat.completions.create(**arguments)

    def evidence(self) -> list[dict]:
        return [
            json.loads(message["content"]) for message in self.messages if message["role"] == "tool"
        ]


class VerifiedDataSources:
    def __init__(self, sources, version: str):
        self.sources = sources
        self.version = version

    async def list_tools(self, context):
        tools = await self.sources.list_tools(context)
        if any(tool["name"] not in {f"data__{name}" for name in QUERIES} for tool in tools):
            raise ValueError("Non-Data catalog in synthetic comparison")
        return tools

    async def call_tool(self, name, arguments, context):
        if name not in {f"data__{tool}" for tool in QUERIES}:
            raise PermissionError("Only synthetic Data tools are allowed")
        response = await self.sources.call_tool(name, arguments, context)
        if (
            response.get("source") != "gaia_synthetic_db"
            or response.get("dataset_version") != self.version
        ):
            raise PermissionError("Comparison dataset mismatch")
        return response


@dataclass
class ComparisonExecutor:
    sources: object
    model: object
    corpus: SyntheticStaticCorpus
    config: ExperimentConfig

    async def execute(self, case: ExperimentCase, condition: str, context: CallContext) -> dict:
        sources, model, corpus, config = self.sources, self.model, self.corpus, self.config
        traced = TracedModel(model)
        question = case.question + ANSWER_CONTRACT
        if condition == "mcp":
            agent = WikiMCPAgent(
                VerifiedDataSources(sources, corpus.version),
                traced,
                "gpt-reserve",
                max_calls=config.max_calls,
                max_evidence_tokens=config.evidence_tokens,
            )
            response = await agent.answer(question, context)
            evidence = traced.evidence()
        else:
            evidence = [corpus.retrieve(case.question, config.evidence_tokens)]
            completion = await traced.create(
                model="gpt-reserve",
                temperature=0,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question},
                    {"role": "user", "content": "Evidenze sintetiche: " + canonical_json(evidence)},
                ],
            )
            if completion.choices[0].message.tool_calls:
                raise RuntimeError("Static answer attempted tool calling")
            response = {"answer": completion.choices[0].message.content or ""}
        return {
            "answer": response["answer"],
            "score": score_answer(case, response["answer"], evidence),
            "evidence": evidence,
            "messages": traced.messages,
            "tool_calls": response.get("tool_calls", 0),
            "evidence_tokens": sum(estimated_tokens(canonical_json(item)) for item in evidence),
        }


async def attempt_result(item: dict, attempt: int, operation) -> dict:
    row = {"item": item, "attempt": attempt, "status": "failed"}
    started = perf_counter()
    try:
        row.update(await operation)
        row["status"] = "completed"
    except Exception as exc:
        row["error_type"] = type(exc).__name__
    row["latency_ms"] = round((perf_counter() - started) * 1000, 3)
    return row


async def run_comparison(cases, corpus, sources, model, config, output: Path) -> list[dict]:
    manifest = experiment_manifest(cases, corpus.version, config)
    journal = ResultJournal(output, manifest)
    case_map = {case.id: case for case in cases}
    executor = ComparisonExecutor(sources, model, corpus, config)
    try:
        for item in schedule(cases, config):
            previous = [row for row in journal.records if row["item"] == item]
            if any(row["status"] == "completed" for row in previous):
                continue
            context = CallContext(
                principal="synthetic-comparison",
                scopes=EXPERIMENT_SCOPES,
                experiment_run_id=str(
                    uuid5(NAMESPACE_URL, manifest["experiment_id"] + canonical_json(item))
                ),
            )
            for attempt in range(len(previous) + 1, config.max_attempts + 1):
                row = await attempt_result(
                    item,
                    attempt,
                    executor.execute(
                        case_map[item["case_id"]],
                        item["condition"],
                        context,
                    ),
                )
                journal.append(row)
                journal.records.append(row)
                if row["status"] == "completed":
                    break
        return journal.records
    finally:
        journal.close()
