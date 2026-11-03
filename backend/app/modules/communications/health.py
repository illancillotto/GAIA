"""Per-process liveness marker; provider health remains a separate DB observation."""

import os
import time
from pathlib import Path


def marker():
    return Path(os.environ.get("COMMUNICATIONS_HEARTBEAT_FILE", "/tmp/communications-heartbeat"))


def mark():
    marker().touch()


def healthy():
    try:
        age = time.time() - marker().stat().st_mtime
        return 0 <= age < float(os.environ.get("COMMUNICATIONS_HEALTH_MAX_AGE", "180"))
    except OSError:
        return False


if __name__ == "__main__":
    raise SystemExit(0 if healthy() else 1)
