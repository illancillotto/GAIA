import importlib.util
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_tool():
    spec = importlib.util.spec_from_file_location(
        "complexity_untracked_test", ROOT / "tools/code_quality/complexity.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_untracked_files_are_wholly_added_and_ignored_files_are_not(tmp_path, monkeypatch):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(
        ["git", "-C", str(tmp_path), "config", "user.email", "test@example.com"], check=True
    )
    subprocess.run(["git", "-C", str(tmp_path), "config", "user.name", "Test"], check=True)
    (tmp_path / ".gitignore").write_text("ignored.ts\n")
    (tmp_path / "tracked.ts").write_text("first\n")
    subprocess.run(["git", "-C", str(tmp_path), "add", "."], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "commit", "-qm", "base"], check=True)
    (tmp_path / "tracked.ts").write_text("first\nsecond\n")
    (tmp_path / "new.ts").write_text("first\nsecond")
    (tmp_path / "empty.ts").write_text("")
    (tmp_path / "with spaces.ts").write_text("first\n")
    (tmp_path / "asset.bin").write_bytes(b"\xff\x00\n\xfe")
    (tmp_path / "ignored.ts").write_text("ignored\n")
    module = load_tool()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    paths = ["tracked.ts", "new.ts", "empty.ts", "with spaces.ts", "asset.bin", "ignored.ts"]
    assert module.added_lines_since("HEAD", paths) == {
        "tracked.ts": {2},
        "new.ts": {1, 2},
        "empty.ts": set(),
        "with spaces.ts": {1},
        "asset.bin": {1, 2},
    }


@pytest.mark.parametrize("failure", ["diff", "untracked"])
def test_git_failures_do_not_invent_added_lines(monkeypatch, failure):
    module = load_tool()
    responses = [subprocess.CompletedProcess([], 1 if failure == "diff" else 0, "", "")]
    if failure == "untracked":
        responses.append(subprocess.CompletedProcess([], 1, "", ""))
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: responses.pop(0))
    assert module.added_lines_since("HEAD", ["new.ts"]) == {}


def test_untracked_listing_failure_preserves_tracked_added_lines(monkeypatch):
    module = load_tool()
    diff = "--- a/tracked.ts\n+++ b/tracked.ts\n@@ -1,0 +2 @@\n+second\n"
    responses = [
        subprocess.CompletedProcess([], 0, diff, ""),
        subprocess.CompletedProcess([], 1, "", ""),
    ]
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kwargs: responses.pop(0))
    assert module.added_lines_since("HEAD", ["tracked.ts"]) == {"tracked.ts": {2}}


@pytest.mark.parametrize(
    "base,paths", [(None, ["new.ts"]), ("HEAD", []), ("HEAD", ["/absolute.ts"])]
)
def test_missing_base_or_repository_paths_skip_git(base, paths, monkeypatch):
    module = load_tool()
    monkeypatch.setattr(
        module.subprocess, "run", lambda *args, **kwargs: pytest.fail("unexpected git call")
    )
    assert module.added_lines_since(base, paths) == {}
