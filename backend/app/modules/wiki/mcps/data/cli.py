"""Explicit offline synthetic seed/reset and read-only stdio server."""

import argparse
import json
import logging
import os
from pathlib import Path

from ..context import CallContext
from ..docs.cli import EventFormatter
from .database import seed_database
from .server import create_server, run_stdio
from .service import DataService


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="GAIA Data MCP (synthetic only)")
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed")
    seed.add_argument("--database", type=Path, required=True)
    seed.add_argument("--seed", default=os.environ.get("GAIA_SYNTHETIC_SEED", "gaia-v1"))
    serve = commands.add_parser("serve")
    serve.add_argument("--database", type=Path, required=True)
    serve.add_argument("--scopes", default="utenze.read,catasto.read,ruolo.read")
    args = parser.parse_args(argv)
    if args.command == "seed":
        manifest = seed_database(args.database, args.seed)
        manifest_path = args.database.with_suffix(".manifest.json")
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        print(json.dumps(manifest))
        return
    handler = logging.StreamHandler()
    handler.setFormatter(EventFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    scopes = frozenset(scope for scope in args.scopes.split(",") if scope)
    service = DataService(args.database)
    try:
        server = create_server(service, lambda: CallContext(principal="local-stdio", scopes=scopes))
        run_stdio(server)
    finally:
        service.close()
