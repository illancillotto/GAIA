"""Make Graphify force updates evict obsolete nodes from re-extracted sources."""

from __future__ import annotations

import importlib
import inspect
import sys
from pathlib import Path

TARGET = (
    "                if changed_paths is not None:\n                    for p in extract_targets:"
)
REPLACEMENT = (
    "                if changed_paths is not None or force:\n"
    "                    for p in extract_targets:"
)


def patch_watch(watch_path: Path) -> str:
    content = watch_path.read_text(encoding="utf-8")
    if content.count(REPLACEMENT) == 1 and TARGET not in content:
        return "already patched"
    if REPLACEMENT in content or content.count(TARGET) != 1:
        raise ValueError(f"expected unique pruning block not found in {watch_path}")
    watch_path.write_text(content.replace(TARGET, REPLACEMENT, 1), encoding="utf-8")
    return "patched"


def main() -> int:
    try:
        graphify = importlib.import_module("graphify")
        watch_path = Path(inspect.getfile(graphify)).with_name("watch.py")
        result = patch_watch(watch_path)
    except (ImportError, OSError, ValueError) as exc:
        print(f"graphify pruning patch failed: {exc}", file=sys.stderr)
        return 1
    print(f"{result}: {watch_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
