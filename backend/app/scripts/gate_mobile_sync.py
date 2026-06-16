from __future__ import annotations

import asyncio
import logging

import httpx

from app.core.config import Settings, settings
from app.core.database import SessionLocal
from app.services.gate_mobile_sync import execute_gate_mobile_sync

logger = logging.getLogger("gaia.gate_mobile_sync")


def _configure_logging() -> None:
    if logging.getLogger().handlers:
        return
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


async def _main() -> int:
    _configure_logging()
    db = SessionLocal()
    try:
        result = await execute_gate_mobile_sync(
            db,
            app_settings=settings,
            trigger_source=_detect_trigger_source(settings),
        )
        if result.status == "skipped":
            logger.info("gate-mobile sync skipped: run_id=%s reason=%s", result.run_id, result.error_message)
            return 0
        logger.info(
            "gate-mobile sync completed: run_id=%s tasks=%s operators_pushed=%s",
            result.run_id,
            len(result.report.requested_tasks) if result.report is not None else 0,
            result.report.operators_pushed if result.report is not None else 0,
        )
        return 0
    except RuntimeError as exc:
        logger.error("gate-mobile sync configuration error: %s", exc)
        return 1
    except httpx.HTTPStatusError as exc:
        logger.error(
            "gate-mobile sync http error: status=%s method=%s path=%s",
            exc.response.status_code,
            exc.request.method,
            exc.request.url.path,
        )
        return 1
    except httpx.HTTPError as exc:
        logger.error("gate-mobile sync transport error: %s", exc)
        return 1
    except Exception:
        logger.exception("gate-mobile sync unexpected error")
        return 1
    finally:
        db.close()


def main() -> int:
    return asyncio.run(_main())


def _detect_trigger_source(app_settings: Settings) -> str:
    if app_settings.app_env == "production":
        return "systemd_timer_or_manual"
    return "manual_cli"


if __name__ == "__main__":
    raise SystemExit(main())
