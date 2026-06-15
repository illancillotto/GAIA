from __future__ import annotations

import asyncio
import logging

import httpx

from app.core.config import settings
from app.core.database import SessionLocal
from app.services.gate_mobile_sync import run_gate_mobile_sync_once

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
    if not settings.gate_mobile_sync_enabled:
        logger.info("gate-mobile sync skipped: GATE_MOBILE_SYNC_ENABLED=false")
        return 0

    db = SessionLocal()
    try:
        report = await run_gate_mobile_sync_once(db)
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
    else:
        logger.info(
            "gate-mobile sync completed: tasks=%s operators_pushed=%s",
            len(report.requested_tasks),
            report.operators_pushed,
        )
        return 0
    finally:
        db.close()


def main() -> int:
    return asyncio.run(_main())


if __name__ == "__main__":
    raise SystemExit(main())
