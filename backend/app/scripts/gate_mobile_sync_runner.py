from __future__ import annotations

import logging
import os
import signal
import threading

from app.scripts import gate_mobile_sync
from app.worker_health import WorkerHeartbeat

logger = logging.getLogger("gaia.gate_mobile_sync_runner")
DEFAULT_INTERVAL_SECONDS = 300.0
MIN_INTERVAL_SECONDS = 10.0
_shutdown_event = threading.Event()
GATE_MOBILE_HEARTBEAT = WorkerHeartbeat(
    "gate-mobile-sync",
    details={"role": "outbound-sync"},
)


def _interval_seconds() -> float:
    try:
        configured = float(
            os.getenv(
                "GATE_MOBILE_SYNC_INTERVAL_SECONDS",
                str(DEFAULT_INTERVAL_SECONDS),
            )
        )
    except ValueError:
        return DEFAULT_INTERVAL_SECONDS
    return max(configured, MIN_INTERVAL_SECONDS)


def _handle_shutdown(signum: int, _frame: object) -> None:
    logger.info("gate-mobile sync runner stopping after signal %s", signum)
    _shutdown_event.set()


def main() -> int:
    gate_mobile_sync._configure_logging()
    _shutdown_event.clear()
    signal.signal(signal.SIGTERM, _handle_shutdown)
    signal.signal(signal.SIGINT, _handle_shutdown)
    interval = _interval_seconds()
    logger.info("gate-mobile sync runner started; interval_seconds=%s", interval)

    while not _shutdown_event.is_set():
        GATE_MOBILE_HEARTBEAT.touch(status="cycle_running")
        exit_code = gate_mobile_sync.main()
        GATE_MOBILE_HEARTBEAT.touch(
            status="waiting",
            details={"last_exit_code": exit_code},
        )
        if exit_code != 0:
            logger.warning(
                "gate-mobile sync cycle failed; exit_code=%s; retry_in_seconds=%s",
                exit_code,
                interval,
            )
        if _shutdown_event.wait(interval):
            break
    logger.info("gate-mobile sync runner stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
