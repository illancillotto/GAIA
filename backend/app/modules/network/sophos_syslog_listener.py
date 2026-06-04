from __future__ import annotations

import logging
import socketserver
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.network.sophos import ingest_sophos_syslog

logger = logging.getLogger(__name__)


class SophosSyslogListener:
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        firewall_name: str | None = None,
        management_ip: str | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._firewall_name = firewall_name or settings.network_sophos_firewall_default_name
        self._management_ip = management_ip or settings.network_sophos_firewall_management_ip

    def handle_message(self, message: str, client_ip: str | None = None) -> None:
        db = self._session_factory()
        try:
            ingest_sophos_syslog(
                db,
                message=message,
                firewall_name=self._firewall_name,
                management_ip=self._management_ip or client_ip,
            )
        except Exception:
            logger.exception("Failed to ingest Sophos syslog message from %s", client_ip or "unknown")
            db.rollback()
        finally:
            db.close()


class _SophosSyslogUDPHandler(socketserver.BaseRequestHandler):
    def handle(self) -> None:
        data = self.request[0]
        if not isinstance(data, bytes):
            return
        message = data.decode("utf-8", errors="replace").strip()
        if not message:
            return
        listener = getattr(self.server, "listener", None)
        if listener is None:
            return
        client_ip = self.client_address[0] if self.client_address else None
        listener.handle_message(message, client_ip)


class _SophosSyslogUDPServer(socketserver.ThreadingUDPServer):
    allow_reuse_address = True
    daemon_threads = True

    def __init__(self, server_address: tuple[str, int], listener: SophosSyslogListener) -> None:
        super().__init__(server_address, _SophosSyslogUDPHandler)
        self.listener = listener


def run_sophos_syslog_listener() -> None:
    listener = SophosSyslogListener(session_factory=SessionLocal)
    bind_address = (settings.network_sophos_syslog_bind_host, settings.network_sophos_syslog_port)
    with _SophosSyslogUDPServer(bind_address, listener) as server:
        logger.info("Sophos syslog listener active on udp://%s:%s", bind_address[0], bind_address[1])
        server.serve_forever(poll_interval=0.5)
