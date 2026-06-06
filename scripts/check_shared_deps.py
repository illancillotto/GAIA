#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


LINE_RE = re.compile(r"^\s*([A-Za-z0-9_.-]+(?:\[[A-Za-z0-9_,.-]+\])?)\s*([<>=!~].+)?$")


def normalize_package_name(raw_name: str) -> str:
    return raw_name.split("[", 1)[0].strip().lower().replace("_", "-")


def parse_requirements_file(path: Path) -> dict[str, str]:
    requirements: dict[str, str] = {}
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        candidate = raw_line.split("#", 1)[0].strip()
        if not candidate or candidate.startswith(("-r", "--requirement", "-c", "--constraint")):
            continue
        match = LINE_RE.match(candidate)
        if not match:
            raise ValueError(f"{path}:{line_number}: unsupported requirement line: {raw_line}")
        package_name = normalize_package_name(match.group(1))
        requirements[package_name] = candidate
    return requirements


def find_shared_dependency_mismatches(left: dict[str, str], right: dict[str, str]) -> list[tuple[str, str, str]]:
    mismatches: list[tuple[str, str, str]] = []
    for package_name in sorted(set(left) & set(right)):
        if left[package_name] != right[package_name]:
            mismatches.append((package_name, left[package_name], right[package_name]))
    return mismatches


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fail when shared dependencies diverge between two requirements files.",
    )
    parser.add_argument("left", type=Path, help="First requirements file")
    parser.add_argument("right", type=Path, help="Second requirements file")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    left_requirements = parse_requirements_file(args.left)
    right_requirements = parse_requirements_file(args.right)
    mismatches = find_shared_dependency_mismatches(left_requirements, right_requirements)

    if not mismatches:
        print(
            f"Shared dependency check passed for {args.left} and {args.right}.",
            file=sys.stdout,
        )
        return 0

    print("Shared dependency mismatch detected:", file=sys.stderr)
    for package_name, left_value, right_value in mismatches:
        print(f" - {package_name}: {args.left} -> {left_value} | {args.right} -> {right_value}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
