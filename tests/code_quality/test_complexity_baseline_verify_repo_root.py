"""baseline-verify must not depend on the checkout path that generated the baseline."""

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/code_quality/complexity.py"
OTHER_CHECKOUT = "/elsewhere/GAIA-generating-checkout"
VERDICT = '"baseline_reproducible_ignoring_timestamp_commit": {}'


def run_tool(*args):
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=ROOT,
        text=True,
        capture_output=True,
    )


def write_baseline_from_other_checkout(tmp_path, **provenance):
    source = tmp_path / "backend/app/example.py"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_text("def ok(x):\n    return x + 1\n")
    baseline = tmp_path / "baseline.json"
    assert run_tool("baseline", "--baseline", str(baseline), str(source)).returncode == 0
    data = json.loads(baseline.read_text())
    assert data["provenance"]["repo_root"] == ROOT.as_posix()
    data["provenance"].update(repo_root=OTHER_CHECKOUT, **provenance)
    baseline.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")
    return source, baseline


def test_baseline_verify_ignores_checkout_repo_root(tmp_path):
    source, baseline = write_baseline_from_other_checkout(tmp_path)

    verified = run_tool("baseline-verify", "--baseline", str(baseline), str(source))

    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert VERDICT.format("true") in verified.stdout


def test_baseline_verify_detects_source_change_despite_other_repo_root(tmp_path):
    source, baseline = write_baseline_from_other_checkout(tmp_path)
    source.write_text("def ok(x):\n    if x:\n        return x + 1\n    return 0\n")

    verified = run_tool("baseline-verify", "--baseline", str(baseline), str(source))

    assert verified.returncode == 1
    assert VERDICT.format("false") in verified.stdout


def test_baseline_verify_still_compares_other_provenance_fields(tmp_path):
    source, baseline = write_baseline_from_other_checkout(
        tmp_path, tool="tools/code_quality/other_tool.py"
    )

    verified = run_tool("baseline-verify", "--baseline", str(baseline), str(source))

    assert verified.returncode == 1
    assert VERDICT.format("false") in verified.stdout
