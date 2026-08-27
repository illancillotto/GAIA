from __future__ import annotations

import importlib.util
import json
import runpy
import sys
from argparse import Namespace
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_changed_worker_coverage.py"
SPEC = importlib.util.spec_from_file_location("check_changed_worker_coverage", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
coverage_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(coverage_gate)


def _args(coverage_json: Path) -> Namespace:
    return Namespace(
        coverage_json=str(coverage_json),
        base_sha="base",
        head_sha="head",
        min_coverage=100.0,
    )


def _write_coverage(path: Path, files: dict[str, float]) -> None:
    path.write_text(
        json.dumps(
            {
                "files": {
                    filename: {"summary": {"percent_covered": percent}}
                    for filename, percent in files.items()
                }
            }
        )
    )


def test_runtime_scope_and_coverage_key_resolution() -> None:
    runtime = "modules/elaborazioni/worker/worker.py"
    assert coverage_gate.is_runtime_worker_file(runtime)
    assert not coverage_gate.is_runtime_worker_file(
        "modules/elaborazioni/worker/tests/test_worker.py"
    )
    assert not coverage_gate.is_runtime_worker_file(
        "modules/elaborazioni/worker/__init__.py"
    )
    assert coverage_gate.resolve_coverage_key(runtime, {"worker.py": 100.0}) == "worker.py"
    absolute = "/workspace/modules/elaborazioni/worker/worker.py"
    assert coverage_gate.resolve_coverage_key(runtime, {absolute: 100.0}) == absolute
    assert coverage_gate.resolve_coverage_key("other/worker.py", {}) is None


def test_parse_args_and_git_changed_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--coverage-json",
            "coverage.json",
            "--base-sha",
            "base",
            "--head-sha",
            "head",
        ],
    )
    args = coverage_gate.parse_args()
    assert args.coverage_json == "coverage.json"
    assert args.min_coverage == 100.0

    monkeypatch.setattr(
        coverage_gate.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(stdout="worker.py\n\n browser.py \n"),
    )
    assert coverage_gate.git_changed_files("base", "head") == ["worker.py", "browser.py"]


def test_load_coverage_ignores_invalid_percentages(tmp_path: Path) -> None:
    report = tmp_path / "coverage.json"
    report.write_text(
        json.dumps(
            {
                "files": {
                    "worker.py": {"summary": {"percent_covered": 100}},
                    "invalid.py": {"summary": {"percent_covered": "100"}},
                }
            }
        )
    )
    assert coverage_gate.load_coverage(report) == {"worker.py": 100.0}


def test_main_passes_when_no_runtime_worker_files_changed(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "coverage.json"
    monkeypatch.setattr(coverage_gate, "parse_args", lambda: _args(report))
    monkeypatch.setattr(
        coverage_gate,
        "git_changed_files",
        lambda *_: ["backend/app/main.py", "modules/elaborazioni/worker/tests/test_worker.py"],
    )

    assert coverage_gate.main() == 0
    assert "No changed worker runtime files" in capsys.readouterr().out


def test_main_reports_missing_and_below_threshold_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "coverage.json"
    _write_coverage(report, {"worker.py": 99.9})
    monkeypatch.setattr(coverage_gate, "parse_args", lambda: _args(report))
    monkeypatch.setattr(
        coverage_gate,
        "git_changed_files",
        lambda *_: [
            "modules/elaborazioni/worker/worker.py",
            "modules/elaborazioni/worker/browser_session.py",
        ],
    )

    assert coverage_gate.main() == 1
    output = capsys.readouterr().out
    assert "worker.py: 99.9%" in output
    assert "browser_session.py: missing" in output


def test_main_passes_all_changed_runtime_files(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report = tmp_path / "coverage.json"
    _write_coverage(report, {"worker.py": 100.0, "browser_session.py": 100.0})
    monkeypatch.setattr(coverage_gate, "parse_args", lambda: _args(report))
    monkeypatch.setattr(
        coverage_gate,
        "git_changed_files",
        lambda *_: [
            "modules/elaborazioni/worker/worker.py",
            "modules/elaborazioni/worker/browser_session.py",
        ],
    )

    assert coverage_gate.main() == 0
    output = capsys.readouterr().out
    assert "passed for 2 changed worker file(s)" in output
    assert output.count("100.0%") == 2


def test_script_entrypoint_exits_cleanly_without_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        sys,
        "argv",
        [
            str(SCRIPT),
            "--coverage-json",
            "unused.json",
            "--base-sha",
            "HEAD",
            "--head-sha",
            "HEAD",
        ],
    )
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert raised.value.code == 0
