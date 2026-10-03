"""SDK source server with schemas generated from strict application inputs."""

import json
from collections.abc import Callable

import anyio
from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from ..context import CallContext
from .catalog import SERVER_INSTRUCTIONS, TOOL_DESCRIPTIONS
from .inputs import INPUTS
from .queries import QUERIES
from .service import SERVER_VERSION, DataService


def create_server(service: DataService, context_factory: Callable[[], CallContext]) -> Server:
    async def list_tools(_context, _params):
        context = context_factory()
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name=name,
                    description=TOOL_DESCRIPTIONS[name] + f" Requires {QUERIES[name].scope}.",
                    input_schema=model.model_json_schema(),
                    annotations=types.ToolAnnotations(
                        read_only_hint=True, destructive_hint=False, open_world_hint=False
                    ),
                )
                for name, model in sorted(INPUTS.items())
                if QUERIES[name].scope in context.scopes
            ]
        )

    async def call_tool(_context, params):
        result = service.call(params.name, params.arguments or {}, context_factory())
        return types.CallToolResult(
            content=[types.TextContent(type="text", text=json.dumps(result, ensure_ascii=False))],
            structured_content=result,
            is_error="error" in result,
        )

    return Server(
        "GAIA Data MCP",
        version=SERVER_VERSION,
        instructions=SERVER_INSTRUCTIONS,
        on_list_tools=list_tools,
        on_call_tool=call_tool,
    )


async def serve_stdio(server: Server) -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def run_stdio(server: Server) -> None:
    anyio.run(serve_stdio, server)
