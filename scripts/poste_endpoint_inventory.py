"""Run locally on a private HAR; output contains no payload/header/query values."""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

# Standalone CLI needs the repository backend on sys.path, not an installed app.
from app.modules.ruolo.services.poste_endpoint_inventory import inventory_har


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("har", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reviewed-path", action="append", default=[])
    args = parser.parse_args(argv)
    try:
        with args.har.open("rb") as source:
            content = source.read(32 * 1024 * 1024 + 1)
        report = inventory_har(content, reviewed_paths=frozenset(args.reviewed_path))
        # Exclusive creation avoids clobbering a capture or following a symlink.
        descriptor = os.open(args.output, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(report, output, ensure_ascii=True, indent=2)
            output.write("\n")
    except (OSError, ValueError):
        parser.exit(2, "Inventario non creato: verificare HAR, dimensione e destinazione nuova.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
