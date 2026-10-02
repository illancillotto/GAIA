import ast
import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def tool():
    spec = importlib.util.spec_from_file_location(
        "complexity_contracts", ROOT / "tools/code_quality/complexity.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def report(tool, tmp_path, monkeypatch):
    source = tmp_path / "backend/app/example.py"
    source.parent.mkdir(parents=True)
    source.write_text("def example(value):\n    return value\n")
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "load_exceptions", lambda: [])
    return tool.scan([str(source)])


def test_callable_identity_and_python_class_metrics(tool, tmp_path):
    source = tmp_path / "classes.py"
    source.write_text(
        "class Parent:\n"
        "    def method(self, value, /, *items, flag=True, **options):\n"
        "        return [item for item in items if item or value or flag]\n"
        "    class Nested:\n"
        "        async def other(self):\n"
        "            return None\n"
    )
    calls, metrics = tool.scan_python(source)
    assert [call.name for call in calls] == ["Parent.method", "Parent.Nested.other"]
    assert calls[0].params == 5
    assert calls[0].cyclomatic == 5
    assert calls[0].key() == f"{source}::Parent.method"
    assert metrics["imports"] == 0
    assert tool.py_param_count(ast.parse("VALUE = 1")) == 0
    assert tool.effective_loc(["", "# comment", "// comment", "value"], 1, 4) == 1


def test_default_scope_excludes_generated_files(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    for name in ["backend/app/ok.py", "frontend/src/a.ts", "frontend/src/a.d.ts"]:
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("")
    assert [tool.rel(path) for path in tool.iter_scope()] == [
        "backend/app/ok.py",
        "frontend/src/a.ts",
    ]
    assert tool.iter_scope(["missing", "frontend/src/a.d.ts"]) == []
    assert tool.iter_scope(["backend/app"]) == [tmp_path / "backend/app/ok.py"]


@pytest.mark.parametrize("available,probe", [(False, 1), (True, 1), (True, 0)])
def test_engine_dependency_availability(tool, monkeypatch, available, probe):
    monkeypatch.setattr(tool, "shutil_which", lambda command: "/bin/node" if available else None)
    responses = [subprocess.CompletedProcess([], 0, "v20\n")]
    responses.append(subprocess.CompletedProcess([], probe, "parser"))
    monkeypatch.setattr(tool.subprocess, "run", lambda *args, **kwargs: responses.pop(0))
    engines = tool.engine_versions()["javascript"]
    assert engines["runtime"] == ("v20" if available else "missing")
    assert engines["@babel/parser"] == ("available" if available and probe == 0 else "missing")


@pytest.mark.parametrize("stderr,stdout", [("git failure", ""), ("", "git failure")])
def test_git_error_diagnostics(tool, monkeypatch, stderr, stdout):
    monkeypatch.setattr(
        tool.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 1, stdout, stderr),
    )
    with pytest.raises(RuntimeError, match="git failure"):
        tool.run_git(["status"])
    assert tool.run_git(["status"], check=False) == stdout


def test_source_commit_without_git_metadata(tool, monkeypatch):
    monkeypatch.setattr(tool, "run_git", lambda *args, **kwargs: "")
    assert tool.source_commit() == "unknown"


def test_merge_base_rejects_success_without_a_commit(tool, monkeypatch):
    monkeypatch.setattr(
        tool.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess([], 0, "  ", ""),
    )
    with pytest.raises(RuntimeError, match="merge-base unavailable"):
        tool.merge_base("main")


def test_merge_base_returns_authoritative_commit(tool, monkeypatch):
    def git_result(command, **kwargs):
        assert command == ["git", "merge-base", "main", "HEAD"]
        assert kwargs["cwd"] == tool.ROOT
        return subprocess.CompletedProcess(command, 0, "reviewed-sha\n", "")

    monkeypatch.setattr(tool.subprocess, "run", git_result)
    assert tool.merge_base("main") == "reviewed-sha"


@pytest.mark.parametrize("failure", ["node", "stderr", "stdout", "silent"])
def test_js_parser_dependency_and_process_failures(tool, tmp_path, monkeypatch, failure):
    monkeypatch.setattr(tool, "shutil_which", lambda command: None if failure == "node" else "node")
    monkeypatch.setattr(
        tool.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [],
            1,
            "parser stdout" if failure == "stdout" else "",
            "parser stderr" if failure == "stderr" else "",
        ),
    )
    message = {
        "node": "node is required",
        "stderr": "parser stderr",
        "stdout": "parser stdout",
        "silent": "JS AST helper failed",
    }[failure]
    with pytest.raises(RuntimeError, match=message):
        tool.scan_js(tmp_path / "invalid.ts")


def test_js_metrics_enforce_thresholds(tool, tmp_path):
    source = tmp_path / "complex.ts"
    source.write_text(
        "export function branch(value: number) {\n"
        + "\n".join(f"if (value === {index}) return {index};" for index in range(20))
        + "\nreturn value;\n}"
    )
    calls, _ = tool.scan_js(source)
    assert any(violation["severity"] == "error" for violation in calls[0].violations)


def test_exception_formats_validation_and_matching(tool, tmp_path):
    path = tmp_path / "exceptions.json"
    assert tool.load_exceptions(path) == []
    entries = [{"pattern": "frontend/src/example.ts", "metric": "*"}]
    path.write_text(json.dumps(entries))
    assert tool.load_exceptions(path) == entries
    errors = tool.validate_exceptions([{}, {"path": "module/**"}])
    assert "exception[0] missing path/pattern" in errors
    assert "exception[0] missing expires_at or no_expiry_reason" in errors
    assert "exception[1] too broad: module/**" in errors
    assert tool.is_path_exception("frontend/src/example.ts", {"metric": "loc"}, entries)
    assert not tool.is_path_exception("frontend/src/other.ts", {"metric": "loc"}, entries)
    assert not tool.is_path_exception(
        "any", {"metric": "loc"}, [{}, {"path": "any", "metric": "params"}]
    )
    valid = {
        "path": "example.py",
        "metric": "loc",
        "reason": "mapping",
        "owner": "qa",
        "introduced_at": "2026-01-01",
        "no_expiry_reason": "fixed declarative schema",
    }
    assert tool.validate_exceptions([valid]) == []


def test_scan_reports_parse_errors_and_respects_exceptions(tool, tmp_path, monkeypatch):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    source = tmp_path / "backend/app/large.py"
    source.parent.mkdir(parents=True)
    source.write_text("\n".join(f"VALUE_{index} = {index}" for index in range(800)))
    broken = source.with_name("broken.py")
    broken.write_text("def invalid(:")
    monkeypatch.setattr(
        tool, "load_exceptions", lambda: [{"path": "backend/app/large.py", "metric": "loc"}]
    )
    data = tool.scan([str(source), str(broken)])
    assert data["parse_errors"][0]["path"] == "backend/app/broken.py"
    assert data["files"]["backend/app/large.py"]["violations"][0]["excepted"] is True
    assert data["violations"] == []
    assert tool.compare(data, None)[0] == 2


def test_integrity_and_scope_reject_malformed_baselines(tool):
    errors = tool.baseline_integrity_errors(
        {"schema_version": -1, "files": {"a": {}}, "callables": {}}
    )
    assert {item["reason"] for item in errors} == {
        "invalid_baseline_schema_version",
        "invalid_baseline_missing_key",
    }
    assert tool.scope_policy_errors({"scope": None}, {"scope": None}) == []
    assert tool.comparable_engines({"custom": "v1"}) == {"custom": "v1"}


def test_scope_include_cannot_silently_drop_runtime(tool):
    old = {"scope": {"include": ["backend/app/**/*.py", "frontend/src/**/*.ts"]}}
    new = {"scope": {"include": ["backend/app/**/*.py"]}}
    assert tool.scope_policy_errors(old, new) == [
        {
            "reason": "baseline_scope_include_changed",
            "old": old["scope"]["include"],
            "new": new["scope"]["include"],
        }
    ]


def test_position_tiebreak_and_added_span_contracts(tool):
    call = {"path": "a", "line": 10, "end_line": 12}
    assert tool.unique_line_tiebreak(call, []) is None
    assert tool.unique_line_tiebreak(call, [{"line": 10}]) == {"line": 10}
    assert tool.unique_line_tiebreak(call, [{"line": 1}, {"line": 30}]) == {"line": 1}
    assert tool.unique_line_tiebreak(call, [{"line": 10}, {"line": 11}]) is None
    assert not tool.callable_is_wholly_added(call, {"a": {10, 12}})
    assert tool.callable_is_wholly_added(call, {"a": {10, 11, 12}})
    assert not tool.callable_is_wholly_added({"path": "a"}, {"a": {1}})


def test_changed_files_combines_commit_worktree_and_untracked(tool, monkeypatch):
    monkeypatch.setattr(tool, "merge_base", lambda base: "base-sha")
    responses = iter(["committed.py\nshared.py", "shared.py\nmodified.py", "new.py"])
    monkeypatch.setattr(tool, "run_git", lambda args: next(responses))
    assert tool.changed_files("main") == {"committed.py", "shared.py", "modified.py", "new.py"}


@pytest.mark.parametrize("failure", ["outside", "missing", "json"])
def test_authoritative_baseline_failures(tool, tmp_path, monkeypatch, failure):
    monkeypatch.setattr(tool, "ROOT", tmp_path)
    monkeypatch.setattr(tool, "merge_base", lambda base: "base-sha")
    path = tmp_path.parent / "outside.json" if failure == "outside" else tmp_path / "baseline.json"
    monkeypatch.setattr(
        tool.subprocess,
        "run",
        lambda *args, **kwargs: subprocess.CompletedProcess(
            [], 1 if failure == "missing" else 0, "{invalid", ""
        ),
    )
    message = {
        "outside": "must be inside",
        "missing": "baseline unavailable",
        "json": "invalid baseline JSON",
    }[failure]
    with pytest.raises(RuntimeError, match=message):
        tool.baseline_at_merge_base("main", path)


def command_args(path):
    return SimpleNamespace(
        paths=[], baseline=str(path), base_ref="main", allow_engine_migration=False
    )


@pytest.mark.parametrize("command", ["changed", "ratchet"])
def test_cli_configuration_failures(tool, tmp_path, monkeypatch, capsys, command):
    def fail(*args, **kwargs):
        raise RuntimeError("unavailable git reference")

    monkeypatch.setattr(tool, "merge_base", fail)
    assert getattr(tool, f"cmd_{command}")(command_args(tmp_path / "baseline.json")) == 2
    assert "unavailable git reference" in capsys.readouterr().err


@pytest.mark.parametrize("command", ["changed", "baseline", "baseline_verify"])
def test_cli_invalid_json_never_rewrites_baseline(
    tool, report, tmp_path, monkeypatch, capsys, command
):
    path = tmp_path / "baseline.json"
    path.write_text("{invalid")
    monkeypatch.setattr(tool, "scan", lambda paths: report)
    monkeypatch.setattr(tool, "merge_base", lambda base: "base")
    monkeypatch.setattr(tool, "changed_files", lambda *args, **kwargs: set())
    assert getattr(tool, f"cmd_{command}")(command_args(path)) == 2
    assert "invalid JSON" in capsys.readouterr().err
    assert path.read_text() == "{invalid"


@pytest.mark.parametrize("command", ["ratchet", "baseline"])
@pytest.mark.parametrize("change", ["scope", "engine"])
def test_cli_rejects_policy_drift(tool, report, tmp_path, monkeypatch, capsys, command, change):
    path = tmp_path / "baseline.json"
    baseline = tool.baseline_from_report(copy.deepcopy(report))
    if change == "scope":
        baseline["scope"]["exclude"] = ["backend/app/**"]
    else:
        baseline["engines"]["python"]["version"] = "old"
    original = json.dumps(baseline)
    path.write_text(original)
    monkeypatch.setattr(tool, "scan", lambda paths: report)
    monkeypatch.setattr(tool, "baseline_at_merge_base", lambda *args: ("base", baseline))
    monkeypatch.setattr(tool, "changed_files", lambda *args, **kwargs: set())
    assert getattr(tool, f"cmd_{command}")(command_args(path)) == 2
    assert ("scope" if change == "scope" else "engine") in capsys.readouterr().err
    assert path.read_text() == original


def test_changed_command_limits_comparison_to_changed_paths(
    tool, report, tmp_path, monkeypatch, capsys
):
    path = tmp_path / "baseline.json"
    baseline = tool.baseline_from_report(copy.deepcopy(report))
    path.write_text(json.dumps(baseline))
    report["callables"][0]["cognitive"] += 100
    report["files"]["backend/app/example.py"]["loc"] = 999
    monkeypatch.setattr(tool, "scan", lambda paths: report)
    monkeypatch.setattr(tool, "merge_base", lambda base: "base")
    monkeypatch.setattr(tool, "changed_files", lambda *args, **kwargs: {"unrelated.py"})
    assert tool.cmd_changed(command_args(path)) == 0
    assert json.loads(capsys.readouterr().out)["findings"] == []


def test_baseline_engine_migration_requires_approval(tool, report, tmp_path, monkeypatch):
    baseline = tool.baseline_from_report(copy.deepcopy(report))
    baseline["engines"]["python"]["version"] = "old"
    path = tmp_path / "baseline.json"
    path.write_text(json.dumps(baseline))
    monkeypatch.setattr(tool, "scan", lambda paths: report)
    args = command_args(path)
    args.allow_engine_migration = True
    assert tool.cmd_baseline(args) == 0
    assert json.loads(path.read_text())["engines"] == report["engines"]


def test_verify_handles_legacy_metadata_shapes_without_mutation(
    tool, report, tmp_path, monkeypatch
):
    report["provenance"] = None
    report["engines"] = {"custom": "v1"}
    baseline = tool.baseline_from_report(report)
    path = tmp_path / "baseline.json"
    original = json.dumps(baseline)
    path.write_text(original)
    monkeypatch.setattr(tool, "scan", lambda paths: report)
    assert tool.cmd_baseline_verify(command_args(path)) == 0
    assert path.read_text() == original
    report["engines"] = None
    path.write_text(json.dumps(tool.baseline_from_report(report)))
    assert tool.cmd_baseline_verify(command_args(path)) == 0


def test_new_file_error_is_reported_but_excepted_error_is_not(tool, report):
    baseline = tool.baseline_from_report(copy.deepcopy(report))
    baseline["files"] = {}
    baseline["callables"] = []
    report["files"]["backend/app/example.py"]["violations"] = [
        {"metric": "loc", "severity": "error", "value": 800},
        {"metric": "useState", "severity": "error", "value": 20, "excepted": True},
    ]
    code, findings = tool.compare(report, baseline)
    assert code == 1
    assert [item["reason"] for item in findings] == ["new_file_violation"]
    assert findings[0]["metric"] == "loc"


def test_ratchet_reads_merge_base_and_never_rewrites_local_baseline(
    tool, report, tmp_path, monkeypatch, capsys
):
    baseline = tool.baseline_from_report(copy.deepcopy(report))
    path = tmp_path / "baseline.json"
    path.write_text("unreviewed local baseline")
    monkeypatch.setattr(tool, "scan", lambda paths: report)
    monkeypatch.setattr(tool, "baseline_at_merge_base", lambda *args: ("reviewed-sha", baseline))
    monkeypatch.setattr(tool, "changed_files", lambda *args, **kwargs: {"backend/app/example.py"})
    assert tool.cmd_ratchet(command_args(path)) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["baseline_commit"] == "reviewed-sha"
    assert result["findings"] == []
    assert path.read_text() == "unreviewed local baseline"


@pytest.mark.parametrize(
    "source,expected",
    [
        ("def plain(value):\n    return value\n", (1, 0, 0)),
        (
            "def condition(value):\n    if value:\n        return value\n    return None\n",
            (2, 1, 1),
        ),
        (
            "def nested(value):\n    if value:\n        while value:\n            value -= 1\n    return value\n",
            (3, 3, 2),
        ),
    ],
)
def test_parser_produced_ast_has_descendants_not_back_edges(tool, source, expected):
    function = ast.parse(source).body[0]
    assert all(
        child is not function
        for parent in ast.walk(function)
        for child in ast.iter_child_nodes(parent)
    )
    assert tool.py_complexities(function) == expected
