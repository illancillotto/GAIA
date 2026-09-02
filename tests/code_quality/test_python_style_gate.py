from __future__ import annotations

import importlib.util
import runpy
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/check_changed_python_style.py"
SPEC = importlib.util.spec_from_file_location("check_changed_python_style", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
style_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(style_gate)


def _completed(returncode: int, stdout: str = "", stderr: str = "") -> SimpleNamespace:
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def test_style_python_file_scope() -> None:
    assert style_gate.is_style_python_file("backend/app/main.py")
    assert style_gate.is_style_python_file("backend/tests/test_health.py")
    assert style_gate.is_style_python_file("backend/alembic/env.py")
    assert style_gate.is_style_python_file("modules/elaborazioni/worker/worker.py")
    assert style_gate.is_style_python_file("modules/elaborazioni/worker/tests/test_worker.py")
    assert style_gate.is_style_python_file("scripts/check_changed_python_style.py")
    assert style_gate.is_style_python_file("tools/code_quality/complexity.py")
    assert style_gate.is_style_python_file("tests/code_quality/test_python_style_gate.py")
    assert not style_gate.is_style_python_file(
        "backend/alembic/versions/20260901_1100_autosync_credential_profiles.py"
    )
    assert not style_gate.is_style_python_file("backend/map_collaborators.py")
    assert not style_gate.is_style_python_file("frontend/src/lib/api.ts")
    assert not style_gate.is_style_python_file("docs/CODE_STYLE.md")


def test_parse_args_defaults_to_origin_main() -> None:
    args = style_gate.parse_args([])
    assert args.base_ref == "origin/main"
    assert args.base_sha is None
    assert args.head_sha is None


def test_parse_args_sha_mode_and_rejections() -> None:
    args = style_gate.parse_args(["--base-sha", "abc", "--head-sha", "def"])
    assert args.base_sha == "abc"
    assert args.head_sha == "def"
    assert args.base_ref is None

    with pytest.raises(SystemExit):
        style_gate.parse_args(["--base-sha", "abc"])
    with pytest.raises(SystemExit):
        style_gate.parse_args(["--base-sha", "abc", "--head-sha", "def", "--base-ref", "main"])


def test_git_helpers_and_merge_base(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_output(args: list[str]) -> str:
        calls.append(args)
        if args[0] == "diff" and "--diff-filter=AMR" in args:
            return "backend/app/main.py\n\n scripts/foo.py \n"
        if args[0] == "diff" and "--diff-filter=A" in args:
            return "scripts/foo.py\n"
        if args[:2] == ["ls-files", "--others"]:
            return "tools/new.py\n"
        if args[0] == "merge-base":
            return "mergebase\n"
        raise AssertionError(args)

    monkeypatch.setattr(style_gate, "git_output", fake_output)
    assert style_gate.git_changed_files(["abc...def"]) == [
        "backend/app/main.py",
        "scripts/foo.py",
    ]
    assert style_gate.git_added_files(["abc...def"]) == ["scripts/foo.py"]
    assert style_gate.git_untracked_files() == ["tools/new.py"]
    assert style_gate.resolve_merge_base("origin/main") == "mergebase"
    assert calls[0][0] == "diff"
    assert calls[-1] == ["merge-base", "HEAD", "origin/main"]


def test_git_output_runs_from_repo_root(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        captured["args"] = args[0]
        captured["cwd"] = kwargs["cwd"]
        return SimpleNamespace(stdout="ok\n", stderr="", returncode=0)

    monkeypatch.setattr(style_gate.subprocess, "run", fake_run)
    assert style_gate.git_output(["status"]) == "ok\n"
    assert captured["args"] == ["git", "status"]
    assert captured["cwd"] == style_gate.REPO_ROOT


def test_existing_style_files_skips_missing_and_out_of_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(style_gate, "REPO_ROOT", tmp_path)
    (tmp_path / "backend/app").mkdir(parents=True)
    (tmp_path / "backend/app/main.py").write_text("x = 1\n")
    selected = style_gate.existing_style_files(
        [
            "backend/app/main.py",
            "backend/app/main.py",
            "backend/app/missing.py",
            "README.md",
        ]
    )
    assert selected == ["backend/app/main.py"]


def test_ensure_ruff_and_run_ruff_on_files(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        style_gate,
        "ruff_command",
        lambda args: (
            _completed(0, stdout="ruff 0.16.0\n")
            if args == ["--version"]
            else _completed(1, stdout="E401\n", stderr="boom\n")
        ),
    )
    assert style_gate.ensure_ruff() is None
    code, output = style_gate.run_ruff_on_files(["check"], ["backend/app/main.py"])
    assert code == 1
    assert "E401" in output
    assert "boom" in output
    assert style_gate.run_ruff_on_files(["check"], []) == (0, "")


def test_ensure_ruff_reports_missing_install(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(style_gate, "ruff_command", lambda _args: _completed(1, stderr="no"))
    message = style_gate.ensure_ruff()
    assert message is not None
    assert "backend/requirements.txt" in message


def test_main_passes_when_no_style_files_changed(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(style_gate, "ensure_ruff", lambda: None)
    monkeypatch.setattr(style_gate, "git_changed_files", lambda *_: ["README.md"])
    monkeypatch.setattr(style_gate, "git_added_files", lambda *_: [])
    assert style_gate.main(["--base-sha", "base", "--head-sha", "head"]) == 0
    assert "No changed Python files" in capsys.readouterr().out


def test_main_fails_when_ruff_is_missing(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(style_gate, "ensure_ruff", lambda: "ruff is required")
    assert style_gate.main(["--base-sha", "base", "--head-sha", "head"]) == 2
    assert "ruff is required" in capsys.readouterr().err


def test_main_fails_on_check_without_format_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(style_gate, "ensure_ruff", lambda: None)
    monkeypatch.setattr(style_gate, "git_changed_files", lambda *_: ["backend/app/main.py"])
    monkeypatch.setattr(style_gate, "git_added_files", lambda *_: [])
    monkeypatch.setattr(style_gate, "existing_style_files", lambda paths: list(paths))
    monkeypatch.setattr(
        style_gate,
        "run_ruff_on_files",
        lambda subcommand, files: (1, "F401 unused\n") if subcommand == ["check"] else (0, ""),
    )
    assert style_gate.main(["--base-sha", "base", "--head-sha", "head"]) == 1
    output = capsys.readouterr().out
    assert "ruff check:" in output
    assert "F401 unused" in output
    assert "ruff format --check" not in output


def test_main_reports_check_and_format_failures(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(style_gate, "ensure_ruff", lambda: None)
    monkeypatch.setattr(
        style_gate,
        "git_changed_files",
        lambda *_: ["backend/app/main.py", "scripts/new.py"],
    )
    monkeypatch.setattr(style_gate, "git_added_files", lambda *_: ["scripts/new.py"])
    monkeypatch.setattr(
        style_gate,
        "existing_style_files",
        lambda paths: list(paths),
    )
    monkeypatch.setattr(
        style_gate,
        "run_ruff_on_files",
        lambda subcommand, files: (
            (1, "F401 unused\n") if subcommand == ["check"] else (1, "would reformat\n")
        ),
    )
    assert style_gate.main(["--base-sha", "base", "--head-sha", "head"]) == 1
    output = capsys.readouterr().out
    assert "Python style gate failed" in output
    assert "ruff check:" in output
    assert "F401 unused" in output
    assert "ruff format --check" in output
    assert "would reformat" in output


def test_main_passes_changed_and_added_files(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(style_gate, "ensure_ruff", lambda: None)
    monkeypatch.setattr(
        style_gate,
        "git_changed_files",
        lambda *_: ["backend/app/main.py", "scripts/new.py"],
    )
    monkeypatch.setattr(style_gate, "git_added_files", lambda *_: ["scripts/new.py"])
    monkeypatch.setattr(style_gate, "existing_style_files", lambda paths: list(paths))
    monkeypatch.setattr(style_gate, "run_ruff_on_files", lambda _subcommand, _files: (0, ""))
    assert style_gate.main(["--base-sha", "base", "--head-sha", "head"]) == 0
    output = capsys.readouterr().out
    assert "passed for 2 changed file(s)" in output
    assert "- backend/app/main.py\n" in output
    assert "- scripts/new.py (format checked)" in output


def test_main_local_mode_includes_untracked_files(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(style_gate, "ensure_ruff", lambda: None)
    monkeypatch.setattr(style_gate, "resolve_merge_base", lambda _ref: "mergebase")
    monkeypatch.setattr(
        style_gate,
        "git_changed_files",
        lambda args: ["backend/app/main.py"] if args == ["mergebase"] else [],
    )
    monkeypatch.setattr(style_gate, "git_added_files", lambda _args: [])
    monkeypatch.setattr(style_gate, "git_untracked_files", lambda: ["scripts/untracked.py"])
    monkeypatch.setattr(
        style_gate, "existing_style_files", lambda paths: list(dict.fromkeys(paths))
    )
    seen: list[tuple[list[str], list[str]]] = []

    def fake_run(subcommand: list[str], files: list[str]) -> tuple[int, str]:
        seen.append((subcommand, files))
        return 0, ""

    monkeypatch.setattr(style_gate, "run_ruff_on_files", fake_run)
    assert style_gate.main(["--base-ref", "origin/main"]) == 0
    assert seen[0] == (["check"], ["backend/app/main.py", "scripts/untracked.py"])
    assert seen[1] == (["format", "--check"], ["scripts/untracked.py"])
    assert "format checked" in capsys.readouterr().out


def test_script_entrypoint_exits_cleanly_without_changes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run(command: list[str], **_kwargs: object) -> SimpleNamespace:
        if command[:3] == [sys.executable, "-m", "ruff"]:
            return _completed(0, stdout="ruff 0.16.0\n")
        if command[:2] == ["git", "diff"]:
            return _completed(0, stdout="")
        raise AssertionError(command)

    monkeypatch.setattr(sys, "argv", [str(SCRIPT), "--base-sha", "HEAD", "--head-sha", "HEAD"])
    monkeypatch.setattr("subprocess.run", fake_run)
    with pytest.raises(SystemExit) as raised:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert raised.value.code == 0


def test_print_block_omits_blank_output(capsys: pytest.CaptureFixture[str]) -> None:
    style_gate.print_block("title:", "  \n")
    assert capsys.readouterr().out == "title:\n"


def test_ruff_command_invokes_module(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, object] = {}

    def fake_run(*args: object, **kwargs: object) -> SimpleNamespace:
        captured["args"] = args[0]
        captured["cwd"] = kwargs["cwd"]
        return _completed(0, stdout="ok")

    monkeypatch.setattr(style_gate.subprocess, "run", fake_run)
    result = style_gate.ruff_command(["--version"])
    assert result.returncode == 0
    assert captured["args"] == [sys.executable, "-m", "ruff", "--version"]
    assert captured["cwd"] == style_gate.REPO_ROOT
