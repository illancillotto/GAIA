#!/usr/bin/env python3
"""Fail when changed Python files in the style perimeter do not pass Ruff."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
RUFF_CONFIG = REPO_ROOT / "ruff.toml"

STYLE_ROOTS: tuple[tuple[str, ...], ...] = (
    ("backend", "app"),
    ("backend", "tests"),
    ("backend", "alembic"),
    ("modules", "elaborazioni", "worker"),
    ("scripts",),
    ("tools",),
    ("tests", "code_quality"),
)

ALEMBIC_VERSIONS = ("backend", "alembic", "versions")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fail if changed Python files in the GAIA style perimeter do not pass Ruff.",
    )
    parser.add_argument("--base-sha", help="Base git SHA for a CI commit range.")
    parser.add_argument("--head-sha", help="Head git SHA for a CI commit range.")
    parser.add_argument(
        "--base-ref",
        help="Git ref compared with the working tree. Defaults to origin/main in local mode.",
    )
    args = parser.parse_args(argv)
    sha_mode = args.base_sha is not None or args.head_sha is not None
    if sha_mode and (not args.base_sha or not args.head_sha):
        parser.error("--base-sha and --head-sha must be provided together.")
    if sha_mode and args.base_ref:
        parser.error("Use either --base-sha/--head-sha or --base-ref, not both.")
    if not sha_mode and not args.base_ref:
        args.base_ref = "origin/main"
    return args


def is_style_python_file(path: str) -> bool:
    pure = Path(path)
    if pure.suffix != ".py":
        return False
    parts = pure.parts
    if parts[:3] == ALEMBIC_VERSIONS:
        return False
    return any(parts[: len(root)] == root for root in STYLE_ROOTS)


def git_output(args: list[str]) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def git_changed_files(revision_args: list[str]) -> list[str]:
    output = git_output(["diff", "--name-only", "--diff-filter=AMR", *revision_args])
    return [line.strip() for line in output.splitlines() if line.strip()]


def git_added_files(revision_args: list[str]) -> list[str]:
    output = git_output(["diff", "--name-only", "--diff-filter=A", *revision_args])
    return [line.strip() for line in output.splitlines() if line.strip()]


def git_untracked_files() -> list[str]:
    output = git_output(["ls-files", "--others", "--exclude-standard"])
    return [line.strip() for line in output.splitlines() if line.strip()]


def resolve_merge_base(base_ref: str) -> str:
    return git_output(["merge-base", "HEAD", base_ref]).strip()


def existing_style_files(paths: list[str]) -> list[str]:
    selected: list[str] = []
    seen: set[str] = set()
    for path in paths:
        if path in seen or not is_style_python_file(path):
            continue
        if not (REPO_ROOT / path).is_file():
            continue
        selected.append(path)
        seen.add(path)
    return selected


def ruff_command(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ruff", *args],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def ensure_ruff() -> str | None:
    result = ruff_command(["--version"])
    if result.returncode != 0:
        return (
            "ruff is required for the Python style gate. "
            "Install backend/requirements.txt in the interpreter running this script."
        )
    return None


def run_ruff_on_files(subcommand: list[str], files: list[str]) -> tuple[int, str]:
    if not files:
        return 0, ""
    result = ruff_command([*subcommand, "--config", str(RUFF_CONFIG), *files])
    output = "".join(part for part in (result.stdout, result.stderr) if part)
    return result.returncode, output


def print_block(title: str, output: str) -> None:
    print(title)
    if output.strip():
        print(output.rstrip())


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    missing_ruff = ensure_ruff()
    if missing_ruff:
        print(missing_ruff, file=sys.stderr)
        return 2

    if args.base_sha:
        revision_args = [f"{args.base_sha}...{args.head_sha}"]
        changed = git_changed_files(revision_args)
        added = git_added_files(revision_args)
    else:
        merge_base = resolve_merge_base(args.base_ref)
        revision_args = [merge_base]
        changed = git_changed_files(revision_args) + git_untracked_files()
        added = git_added_files(revision_args) + git_untracked_files()

    check_files = existing_style_files(changed)
    format_files = existing_style_files(added)
    if not check_files:
        print("No changed Python files in the style perimeter to validate.")
        return 0

    check_code, check_output = run_ruff_on_files(["check"], check_files)
    format_code, format_output = run_ruff_on_files(["format", "--check"], format_files)

    if check_code == 0 and format_code == 0:
        print(f"Python style gate passed for {len(check_files)} changed file(s).")
        for filename in check_files:
            suffix = " (format checked)" if filename in format_files else ""
            print(f"- {filename}{suffix}")
        return 0

    print("Python style gate failed for changed files.")
    if check_code != 0:
        print_block("ruff check:", check_output)
    if format_code != 0:
        print_block("ruff format --check (added files only):", format_output)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
