#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail if changed backend runtime files are below minimum coverage.",
    )
    parser.add_argument("--coverage-json", required=True, help="Path to coverage JSON report.")
    parser.add_argument("--base-sha", required=True, help="Base git SHA for diff.")
    parser.add_argument("--head-sha", required=True, help="Head git SHA for diff.")
    parser.add_argument("--min-coverage", type=float, default=100.0, help="Minimum file coverage percentage.")
    return parser.parse_args()


def git_changed_files(base_sha: str, head_sha: str) -> list[str]:
    result = subprocess.run(
        ["git", "diff", "--name-only", f"{base_sha}...{head_sha}"],
        capture_output=True,
        text=True,
        check=True,
    )
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def load_coverage(path: Path) -> dict[str, float]:
    payload = json.loads(path.read_text())
    files = payload.get("files", {})
    coverage_by_file: dict[str, float] = {}
    for filename, metrics in files.items():
        summary = metrics.get("summary", {})
        percent = summary.get("percent_covered")
        if isinstance(percent, (int, float)):
            coverage_by_file[filename] = float(percent)
    return coverage_by_file


def is_runtime_backend_file(path: str) -> bool:
    pure = Path(path)
    return (
        pure.suffix == ".py"
        and pure.parts[:2] == ("backend", "app")
        and pure.name != "__init__.py"
    )


def resolve_coverage_key(changed_file: str, coverage_by_file: dict[str, float]) -> str | None:
    candidates = [changed_file]
    pure = Path(changed_file)
    if pure.parts[:2] == ("backend", "app"):
        candidates.append(str(Path(*pure.parts[1:])))
    for candidate in candidates:
        if candidate in coverage_by_file:
            return candidate
    return None


def main() -> int:
    args = parse_args()
    changed_files = [path for path in git_changed_files(args.base_sha, args.head_sha) if is_runtime_backend_file(path)]
    if not changed_files:
        print("No changed backend runtime files to validate.")
        return 0

    coverage_by_file = load_coverage(Path(args.coverage_json))

    failures: list[tuple[str, float | None]] = []
    for filename in changed_files:
        coverage_key = resolve_coverage_key(filename, coverage_by_file)
        covered = coverage_by_file.get(coverage_key) if coverage_key else None
        if covered is None or covered < args.min_coverage:
            failures.append((filename, covered))

    if failures:
        print(f"Coverage gate failed for changed backend files. Minimum required: {args.min_coverage:.1f}%")
        for filename, covered in failures:
          value = "missing" if covered is None else f"{covered:.1f}%"
          print(f"- {filename}: {value}")
        return 1

    print(f"Coverage gate passed for {len(changed_files)} changed backend file(s).")
    for filename in changed_files:
        coverage_key = resolve_coverage_key(filename, coverage_by_file)
        print(f"- {filename}: {coverage_by_file[coverage_key]:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
