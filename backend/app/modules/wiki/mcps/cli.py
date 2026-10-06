"""Run the two authenticated internal HTTP adapters in one local process."""

import argparse
import logging
import os
from contextlib import ExitStack, closing
from pathlib import Path

import uvicorn

from .audit import AuditStore
from .auth import validate_secret
from .data.service import DataService
from .docs.cli import EventFormatter
from .docs.corpus import load_corpus
from .docs.service import DocsService
from .http import create_http_app


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="GAIA internal MCP HTTP sources")
    parser.add_argument("--corpus", type=Path)
    parser.add_argument("--data-only", action="store_true")
    parser.add_argument("--database", type=Path, required=True)
    parser.add_argument("--audit-database", type=Path)
    parser.add_argument("--host", choices=["127.0.0.1", "0.0.0.0"], default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8768)
    args = parser.parse_args(argv)
    if args.data_only == (args.corpus is not None):
        parser.error("Choose either --data-only or --corpus")
    secret = os.environ.get("GAIA_MCP_SIGNING_SECRET", "")
    validate_secret(secret)
    handler = logging.StreamHandler()
    handler.setFormatter(EventFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    with ExitStack() as stack:
        audit = None
        if args.audit_database:
            audit = AuditStore(args.audit_database)
            stack.callback(audit.close)
        docs = None
        if not args.data_only:
            docs = DocsService(load_corpus(args.corpus))
            stack.callback(docs.close)
        data = stack.enter_context(closing(DataService(args.database, audit=audit)))
        app = create_http_app(docs, data, secret)
        uvicorn.run(app, host=args.host, port=args.port, access_log=False)
