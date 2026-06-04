from app.core.config import settings
from app.modules.network.sophos_snmp import run_sophos_snmp_poller


def main() -> None:
    if not settings.network_sophos_snmp_enabled:
        raise SystemExit("NETWORK_SOPHOS_SNMP_ENABLED is false")
    run_sophos_snmp_poller()


if __name__ == "__main__":
    main()
