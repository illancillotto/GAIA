#!/usr/bin/env python3
"""Patch local graphify install to honor OPENAI_BASE_URL for the openai backend."""

from __future__ import annotations

import inspect
import os
import sys
from pathlib import Path


TARGET = '"base_url": "https://api.openai.com/v1",'
REPLACEMENT = '"base_url": os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"),'


def main() -> int:
    try:
        import graphify  # type: ignore
    except Exception as exc:
        print(f"graphify import failed: {exc}", file=sys.stderr)
        return 1

    llm_path = Path(inspect.getfile(graphify)).with_name("llm.py")
    content = llm_path.read_text(encoding="utf-8")

    if REPLACEMENT in content:
        print(f"already patched: {llm_path}")
        return 0

    if TARGET not in content:
        print(f"expected target string not found in {llm_path}", file=sys.stderr)
        return 1

    llm_path.write_text(content.replace(TARGET, REPLACEMENT, 1), encoding="utf-8")
    print(f"patched: {llm_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
