import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools/code_quality/complexity.py"


def run_tool(*args, cwd=ROOT):
    return subprocess.run(
        [sys.executable, str(TOOL), *args],
        cwd=cwd,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def test_baseline_verify_ignores_nested_provenance_source_commit(tmp_path):
    source = tmp_path / "backend/app/example.py"
    write(source, "def ok(x):\n    return x + 1\n")
    baseline = tmp_path / "baseline.json"

    assert run_tool("baseline", "--baseline", str(baseline), str(source)).returncode == 0
    data = json.loads(baseline.read_text())
    data["source_commit"] = "old-head"
    data["provenance"]["source_commit"] = "old-head"
    baseline.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    verified = run_tool("baseline-verify", "--baseline", str(baseline), str(source))
    assert verified.returncode == 0, verified.stdout + verified.stderr
    assert '"baseline_reproducible_ignoring_timestamp_commit": true' in verified.stdout


def test_baseline_verify_detects_real_source_change_after_metadata_normalization(tmp_path):
    source = tmp_path / "backend/app/example.py"
    write(source, "def ok(x):\n    return x + 1\n")
    baseline = tmp_path / "baseline.json"

    assert run_tool("baseline", "--baseline", str(baseline), str(source)).returncode == 0
    data = json.loads(baseline.read_text())
    data["source_commit"] = "old-head"
    data["provenance"]["source_commit"] = "old-head"
    baseline.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n")

    write(source, "def ok(x):\n    if x:\n        return x + 1\n    return 0\n")
    verified = run_tool("baseline-verify", "--baseline", str(baseline), str(source))
    assert verified.returncode == 1
    assert '"baseline_reproducible_ignoring_timestamp_commit": false' in verified.stdout
