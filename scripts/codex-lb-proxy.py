#!/usr/bin/env python3
"""
HTTP reverse proxy: ascolta su 0.0.0.0:2455 e forwarda a codex-lb su 127.0.0.1:2456.
Riscrive l'header Host per aggirare il controllo IP di codex-lb.

Avvio: nohup python3 scripts/codex-lb-proxy.py > /tmp/codex-lb-proxy.log 2>&1 &
"""

import http.server
import http.client
import urllib.parse
import sys
import logging

LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 2455
TARGET_HOST = "127.0.0.1"
TARGET_PORT = 2456

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("proxy")


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        log.info("%s %s", self.address_string(), fmt % args)

    def _forward(self, body: bytes | None = None):
        conn = http.client.HTTPConnection(TARGET_HOST, TARGET_PORT, timeout=120)
        headers = {k: v for k, v in self.headers.items()}
        headers["Host"] = f"{TARGET_HOST}:{TARGET_PORT}"
        try:
            conn.request(self.command, self.path, body=body, headers=headers)
            resp = conn.getresponse()
            self.send_response(resp.status, resp.reason)
            for name, value in resp.getheaders():
                if name.lower() in ("transfer-encoding", "connection"):
                    continue
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(resp.read())
        except Exception as exc:
            log.error("upstream error: %s", exc)
            self.send_error(502, str(exc))
        finally:
            conn.close()

    def do_GET(self):
        self._forward()

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        self._forward(body)

    def do_OPTIONS(self):
        self._forward()

    def do_DELETE(self):
        self._forward()

    def do_PATCH(self):
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length) if length else b""
        self._forward(body)


if __name__ == "__main__":
    server = http.server.HTTPServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    log.info("proxy %s:%s → %s:%s", LISTEN_HOST, LISTEN_PORT, TARGET_HOST, TARGET_PORT)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        log.info("stopped")
        sys.exit(0)
