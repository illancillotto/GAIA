from app.core.config import settings
from app.modules.network.scheduler import execute_scheduled_scan, run_scheduler


def main() -> None:
    if settings.network_scan_enabled:
        run_scheduler()
        return
    execute_scheduled_scan()


if __name__ == "__main__":
    main()
