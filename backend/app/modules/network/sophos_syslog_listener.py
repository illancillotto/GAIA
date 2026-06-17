from __future__ import annotations

import logging
import queue
import socketserver
import threading
from typing import Callable

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.modules.network.sophos import ingest_sophos_syslog
from app.modules.network.sophos_runtime import get_sophos_runtime_policy

logger = logging.getLogger(__name__)


class SophosSyslogListener:
    def __init__(
        self,
        *,
        session_factory: Callable[[], Session],
        firewall_name: str | None = None,
        management_ip: str | None = None,
        worker_count: int | None = None,
        queue_size: int | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._firewall_name = firewall_name or settings.network_sophos_firewall_default_name
        self._management_ip = management_ip or settings.network_sophos_firewall_management_ip
        self._worker_count = max(worker_count or settings.network_sophos_syslog_worker_count, 1)
        self._message_queue: queue.Queue[tuple[str, str | None] | None] = queue.Queue(
            maxsize=max(queue_size or settings.network_sophos_syslog_queue_size, 1)
        )
        self._workers: list[threading.Thread] = []
        self._started = False

    def start(self) -> None:
        if self._started:
            return
        self._started = True
        for index in range(self._worker_count):
            worker = threading.Thread(
                target=self._worker_loop,
                name=f"sophos-syslog-worker-{index + 1}",
                daemon=True,
            )
            worker.start()
            self._workers.append(worker)

    def stop(self) -> None:
        if not self._started:
            return
        for _ in self._workers:
            try:
                self._message_queue.put_nowait(None)
            except queue.Full:
                break
        for worker in self._workers:
            worker.join(timeout=2.0)
        self._workers.clear()
        self._started = False

    def enqueue_message(self, message: str, client_ip: str | None = None) -> None:
        try:
            self._message_queue.put_nowait((message, client_ip))
        except queue.Full:
            logger.warning(
                "Dropping Sophos syslog message from %s because the ingest queue is full (%s items).",
                client_ip or "unknown",
                self._message_queue.qsize(),
            )

    def _worker_loop(self) -> None:
        while True:
            item = self._message_queue.get()
            if item is None:
                self._message_queue.task_done()
                break
            message, client_ip = item
            try:
                self.handle_message(message, client_ip)
            finally:
                self._message_queue.task_done()

    def handle_message(self, message: str, client_ip: str | None = None) -> None:
        db = self._session_factory()
        try:
            policy = get_sophos_runtime_policy(db)
            if not policy.syslog_should_ingest:
                logger.debug(
                    "Skipping Sophos syslog ingest from %s because runtime policy disabled processing (window=%s).",
                    client_ip or "unknown",
                    policy.is_within_window,
                )
                return
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
        listener.enqueue_message(message, client_ip)


class _SophosSyslogUDPServer(socketserver.UDPServer):
    allow_reuse_address = True

    def __init__(self, server_address: tuple[str, int], listener: SophosSyslogListener) -> None:
        super().__init__(server_address, _SophosSyslogUDPHandler)
        self.listener = listener


def run_sophos_syslog_listener() -> None:
    listener = SophosSyslogListener(session_factory=SessionLocal)
    listener.start()
    bind_address = (settings.network_sophos_syslog_bind_host, settings.network_sophos_syslog_port)
    try:
        with _SophosSyslogUDPServer(bind_address, listener) as server:
            logger.info(
                "Sophos syslog listener active on udp://%s:%s with %s workers and queue size %s",
                bind_address[0],
                bind_address[1],
                listener._worker_count,
                listener._message_queue.maxsize,
            )
            server.serve_forever(poll_interval=0.5)
    finally:
        listener.stop()
