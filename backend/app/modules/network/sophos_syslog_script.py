from app.core.config import settings
from app.db import base as _db_base  # Ensure SQLAlchemy mappers are fully registered in worker entrypoints.
from app.modules.network.sophos_syslog_listener import run_sophos_syslog_listener


def main() -> None:
    _ = _db_base
    if not settings.network_sophos_syslog_enabled:
        raise SystemExit("NETWORK_SOPHOS_SYSLOG_ENABLED is false")
    run_sophos_syslog_listener()


if __name__ == "__main__":
    main()
