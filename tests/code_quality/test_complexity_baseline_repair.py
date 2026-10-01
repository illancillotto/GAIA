"""A stale baseline can be repaired only from unchanged committed runtime."""

import importlib.util
import json
import sys
from argparse import Namespace
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "repair_complexity", Path(__file__).parents[2] / "tools/code_quality/complexity.py"
)
complexity = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = complexity
SPEC.loader.exec_module(complexity)


@pytest.fixture
def repair(monkeypatch, tmp_path):
    source = tmp_path / "backend/app/example.py"
    source.parent.mkdir(parents=True)
    source.write_text("def example(value):\n    return value + 1\n")
    report = complexity.scan([str(source)])
    path = tmp_path / "baseline.json"
    baseline = complexity.baseline_from_report(report)
    baseline["callables"][0]["loc"] = 1
    path.write_text(json.dumps(baseline))
    monkeypatch.setattr(complexity, "ROOT", tmp_path)
    monkeypatch.setattr(complexity, "DEFAULT_EXCEPTIONS", tmp_path / "config/exceptions.json")
    monkeypatch.setattr(complexity, "changed_files", lambda _: set())
    monkeypatch.setattr(complexity, "load_exceptions", lambda: [])
    monkeypatch.setattr(complexity, "scan", lambda: report)
    return Namespace(paths=[], baseline=str(path)), path, report


def test_repairs_only_the_unchanged_runtime_snapshot(repair):
    args, path, report = repair
    assert complexity.cmd_baseline_repair(args) == 0
    assert json.loads(path.read_text()) == complexity.baseline_from_report(report)


@pytest.mark.parametrize(
    "changed",
    [
        "backend/app/new.py",
        "frontend/src/example.tsx",
        "modules/elaborazioni/worker/example.py",
        "config/exceptions.json",
    ],
)
def test_refuses_feature_or_exception_changes(repair, monkeypatch, changed):
    args, path, _ = repair
    before = path.read_bytes()
    monkeypatch.setattr(complexity, "changed_files", lambda _: {changed})
    assert complexity.cmd_baseline_repair(args) == 2
    assert path.read_bytes() == before


def test_refuses_partial_scope_and_missing_baseline(repair):
    args, path, _ = repair
    args.paths = ["backend/app"]
    assert complexity.cmd_baseline_repair(args) == 2
    args.paths = []
    path.unlink()
    assert complexity.cmd_baseline_repair(args) == 2
    assert not path.exists()


def test_refuses_invalid_exceptions_or_scope_change(repair, monkeypatch):
    args, path, _ = repair
    before = path.read_bytes()
    monkeypatch.setattr(complexity, "validate_exceptions", lambda _: ["invalid exception"])
    assert complexity.cmd_baseline_repair(args) == 2
    monkeypatch.setattr(complexity, "validate_exceptions", lambda _: [])
    monkeypatch.setattr(complexity, "scope_policy_errors", lambda *_: [{"reason": "scope_changed"}])
    assert complexity.cmd_baseline_repair(args) == 2
    assert path.read_bytes() == before
