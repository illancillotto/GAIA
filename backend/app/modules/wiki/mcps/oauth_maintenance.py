"""Traffic-independent OAuth maintenance owned by the connector lifespan."""

import asyncio
import logging
import sqlite3
from contextlib import asynccontextmanager, suppress

logger = logging.getLogger(__name__)


async def cleanup_loop(store, budget):
    while True:
        await asyncio.sleep(store.policy.cleanup_seconds)
        try:
            with store.transaction():
                store.cleanup()
                budget.cleanup()
        except sqlite3.Error:
            logger.error("gaia_mcp_oauth_cleanup_failed")


@asynccontextmanager
async def maintenance(store, budget):
    with store.transaction():
        store.cleanup()
        budget.cleanup()
    task = asyncio.create_task(cleanup_loop(store, budget), name="gaia-mcp-oauth-cleanup")
    try:
        yield
    finally:
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
