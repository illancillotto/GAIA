#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail if changed frontend runtime files are below minimum coverage.",
    )
    parser.add_argument("--coverage-json", required=True, help="Path to coverage JSON report.")
    parser.add_argument("--base-sha", required=True, help="Base git SHA for diff.")
    parser.add_argument("--head-sha", required=True, help="Head git SHA for diff.")
    parser.add_argument("--min-coverage", type=float, default=80.0, help="Minimum file coverage percentage.")
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
    coverage_by_file: dict[str, float] = {}
    for filename, metrics in payload.items():
        if not isinstance(metrics, dict):
            continue
        totals = metrics.get("s")
        if not isinstance(totals, dict) or not totals:
            continue
        covered = sum(1 for value in totals.values() if value > 0)
        total = len(totals)
        coverage_by_file[filename] = (covered / total) * 100 if total else 100.0
    return coverage_by_file


def is_runtime_frontend_file(path: str) -> bool:
    pure = Path(path)
    return (
        pure.suffix in {".ts", ".tsx", ".js", ".jsx"}
        and pure.parts[:2] == ("frontend", "src")
        and "__tests__" not in pure.parts
        and not pure.name.endswith(".d.ts")
        and pure.parts[:3] != ("frontend", "src", "types")
    )


def resolve_coverage_key(changed_file: str, coverage_by_file: dict[str, float]) -> str | None:
    candidates = [changed_file]
    pure = Path(changed_file)
    if pure.parts and pure.parts[0] == "frontend":
        candidates.append(str(Path(*pure.parts[1:])))
    candidates.append(str(pure))
    for candidate in candidates:
        if candidate in coverage_by_file:
            return candidate
    normalized_suffixes = {candidate.replace("\\", "/") for candidate in candidates}
    for coverage_key in coverage_by_file:
        normalized_key = coverage_key.replace("\\", "/")
        if any(normalized_key.endswith(suffix) for suffix in normalized_suffixes):
            return coverage_key
    return None


def main() -> int:
    args = parse_args()
    changed_files = [path for path in git_changed_files(args.base_sha, args.head_sha) if is_runtime_frontend_file(path)]
    if not changed_files:
        print("No changed frontend runtime files to validate.")
        return 0

    coverage_by_file = load_coverage(Path(args.coverage_json))

    failures: list[tuple[str, float | None]] = []
    for filename in changed_files:
        coverage_key = resolve_coverage_key(filename, coverage_by_file)
        covered = coverage_by_file.get(coverage_key) if coverage_key else None
        if covered is None or covered < args.min_coverage:
            failures.append((filename, covered))

    if failures:
        print(f"Coverage gate failed for changed frontend files. Minimum required: {args.min_coverage:.1f}%")
        for filename, covered in failures:
            value = "missing" if covered is None else f"{covered:.1f}%"
            print(f"- {filename}: {value}")
        return 1

    print(f"Coverage gate passed for {len(changed_files)} changed frontend file(s).")
    for filename in changed_files:
        coverage_key = resolve_coverage_key(filename, coverage_by_file)
        print(f"- {filename}: {coverage_by_file[coverage_key]:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
