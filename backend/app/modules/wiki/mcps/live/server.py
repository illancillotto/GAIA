"""MCP protocol boundary for the explicitly approved live read catalog."""

import json

from mcp import types
from mcp.server import Server

from .catalog import TOOLS


def create_server(service):
    async def list_tools(context, params):
        names = await service.tools()
        return types.ListToolsResult(
            tools=[
                types.Tool(
                    name=name,
                    description=TOOLS[name].description,
                    input_schema=TOOLS[name].inputs.model_json_schema(),
                    annotations=types.ToolAnnotations(
                        read_only_hint=True, destructive_hint=False, open_world_hint=False
                    ),
                )
                for name in names
            ]
        )

    async def call_tool(context, params):
        result = await service.call(params.name, params.arguments or {})
        return types.CallToolResult(
            structured_content=result,
            content=[types.TextContent(type="text", text=json.dumps(result))],
            is_error="error" in result,
        )

    return Server(
        "GAIA Live MCP", version="gaia-live-v1", on_list_tools=list_tools, on_call_tool=call_tool
    )
