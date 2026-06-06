from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "check_shared_deps.py"


def test_shared_dependency_guardrail_passes_on_current_requirements() -> None:
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            str(REPO_ROOT / "backend" / "requirements.txt"),
            str(REPO_ROOT / "modules" / "elaborazioni" / "worker" / "requirements.txt"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    assert "Shared dependency check passed" in result.stdout


def test_shared_dependency_guardrail_detects_mismatch(tmp_path: Path) -> None:
    left = tmp_path / "left.txt"
    right = tmp_path / "right.txt"
    left.write_text("playwright==1.55.0\npytest==8.4.2\n", encoding="utf-8")
    right.write_text("playwright==1.40.0\npytest==8.4.2\n", encoding="utf-8")

    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(left), str(right)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "playwright" in result.stderr
    assert "1.55.0" in result.stderr
    assert "1.40.0" in result.stderr
