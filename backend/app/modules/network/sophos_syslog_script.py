from app.core.config import settings
from app.modules.network.sophos_syslog_listener import run_sophos_syslog_listener


def main() -> None:
    if not settings.network_sophos_syslog_enabled:
        raise SystemExit("NETWORK_SOPHOS_SYSLOG_ENABLED is false")
    run_sophos_syslog_listener()


if __name__ == "__main__":
    main()
