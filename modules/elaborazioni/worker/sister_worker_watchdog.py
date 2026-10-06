from __future__ import annotations

import asyncio
import json
import math
import os
import sys
import threading
import time
from collections.abc import Awaitable, Callable
from pathlib import Path


class WorkerWatchdog:
    def __init__(self, path: Path, *, timeout: float = 120, interval: float = 5) -> None:
        if not math.isfinite(timeout) or not math.isfinite(interval) or not 0 < interval < timeout:
            raise ValueError("Watchdog requires finite 0 < interval < timeout")
        self.path = path
        self.timeout = timeout
        self.interval = interval
        self.stopped = threading.Event()
        self.last_progress = time.monotonic()
        self.marker: float | None = None
        self.thread = threading.Thread(
            target=self.monitor, name="sister-worker-watchdog", daemon=True
        )

    def read_marker(self) -> float | None:
        try:
            payload = json.loads(self.path.read_text())
            if not isinstance(payload, dict) or payload.get("pid") != os.getpid():
                return None
            value = payload.get("updated_at_epoch")
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                return None
            return float(value) if math.isfinite(value) else None
        except (OSError, ValueError):
            return None

    def monitor(self) -> None:
        while not self.stopped.wait(self.interval):
            now = time.monotonic()
            marker = self.read_marker()
            if marker is not None and marker != self.marker:
                self.marker = marker
                self.last_progress = now
            if now - self.last_progress >= self.timeout:
                print(
                    "SISTER watchdog: heartbeat fermo; uscita 1 per riavvio del container. "
                    "Nessun reinvio o modifica dati eseguiti dal watchdog.",
                    file=sys.stderr,
                    flush=True,
                )
                os._exit(1)


def run_supervised(
    operation: Callable[[], Awaitable[None]],
    heartbeat_path: Path,
    *,
    timeout: float = 120,
    interval: float = 5,
) -> None:
    watchdog = WorkerWatchdog(heartbeat_path, timeout=timeout, interval=interval)
    watchdog.thread.start()
    try:
        asyncio.run(operation())
    finally:
        watchdog.stopped.set()
        watchdog.thread.join()
