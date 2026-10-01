"""Build frozen corpus artifacts or run the independent local MCP server."""

import argparse
import csv
import json
import logging
from pathlib import Path

from .corpus import Manifest, ManifestEntry, build_corpus, load_corpus
from .server import create_server
from .service import DocsService


class EventFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        return json.dumps(getattr(record, "mcp_event", {"message": record.getMessage()}))


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="GAIA Docs MCP (local, frozen corpus)")
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("build")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--manifest", type=Path, required=True)
    build.add_argument("--output", type=Path, required=True)
    serve = commands.add_parser("serve")
    serve.add_argument("--corpus", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "build":
        manifest = Manifest.model_validate_json(args.manifest.read_bytes())
        corpus = build_corpus(args.root, manifest)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "corpus.json").write_text(corpus.model_dump_json(indent=2), encoding="utf-8")
        version = {
            "format_version": corpus.format_version,
            "corpus_version": corpus.corpus_version,
            "document_count": sum(entry.included for entry in corpus.manifest.entries),
            "chunk_count": len(corpus.chunks),
        }
        (args.output / "corpus_version.json").write_text(
            json.dumps(version, indent=2), encoding="utf-8"
        )
        with (args.output / "corpus_manifest.csv").open(
            "w", encoding="utf-8", newline=""
        ) as handle:
            writer = csv.DictWriter(handle, fieldnames=list(ManifestEntry.model_fields))
            writer.writeheader()
            writer.writerows(entry.model_dump() for entry in corpus.manifest.entries)
        print(json.dumps(version))
        return
    handler = logging.StreamHandler()
    handler.setFormatter(EventFormatter())
    logging.basicConfig(level=logging.INFO, handlers=[handler])
    service = DocsService(load_corpus(args.corpus))
    try:
        create_server(service).run(transport="stdio")
    finally:
        service.close()
