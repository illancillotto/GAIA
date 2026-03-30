from __future__ import annotations

from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import re
import shutil
import subprocess
from urllib.parse import parse_qs, urlparse


MAC_PATTERN = re.compile(
    r"\b([0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2}(?::|-)[0-9a-fA-F]{2})\b"
)


def _normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower().replace("-", ":")
    return normalized or None


def _lookup_mac(ip_address: str) -> str | None:
    commands = (
        ["ip", "neigh", "show", ip_address],
        ["arp", "-n", ip_address],
    )

    for command in commands:
        if shutil.which(command[0]) is None:
            continue
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=1.5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            continue

        if result.returncode != 0:
            continue

        match = MAC_PATTERN.search(result.stdout)
        if match:
            return _normalize_mac(match.group(1))
    return None


class ArpLookupHandler(BaseHTTPRequestHandler):
    server_version = "GAIAArpHelper/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._write_json(HTTPStatus.OK, {"status": "ok"})
            return

        if parsed.path != "/lookup":
            self._write_json(HTTPStatus.NOT_FOUND, {"detail": "Not found"})
            return

        ip_address = parse_qs(parsed.query).get("ip", [None])[0]
        if not ip_address:
            self._write_json(HTTPStatus.BAD_REQUEST, {"detail": "Missing ip query parameter"})
            return

        mac_address = _lookup_mac(ip_address)
        self._write_json(
            HTTPStatus.OK,
            {
                "ip_address": ip_address,
                "mac_address": mac_address,
                "found": bool(mac_address),
            },
        )

    def log_message(self, format: str, *args: object) -> None:
        return

    def _write_json(self, status: HTTPStatus, payload: dict[str, object]) -> None:
        body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
        self.send_response(status.value)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main() -> None:
    server = ThreadingHTTPServer(("0.0.0.0", 9105), ArpLookupHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
