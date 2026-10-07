"""Explicit local launch; neither user credentials nor real records enter config files."""

from contextlib import closing
from pathlib import Path

from ..audit import AuditStore
from ..data.server import serve_stdio
from .api import GaiaAPI
from .server import create_server
from .service import LiveService


async def serve(environ):
    if environ.get("GAIA_MCP_LIVE_ENABLED") != "true":
        raise ValueError("Live MCP requires explicit opt-in; synthetic MCP is unchanged")
    with closing(AuditStore(Path(environ["GAIA_MCP_LIVE_AUDIT"]))) as audit:
        api = GaiaAPI(
            environ["GAIA_MCP_LIVE_ORIGIN"],
            environ["GAIA_MCP_LIVE_TOKEN"],
            ca_file=environ.get("GAIA_MCP_LIVE_CA_FILE"),
        )
        try:
            service = LiveService(api, audit, environ["GAIA_MCP_LIVE_TOOLS"].split(","))
            await serve_stdio(create_server(service))
        finally:
            await api.close()
