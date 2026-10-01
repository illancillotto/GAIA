"""Wiki-facing SDK client; namespaced tools keep sources distinct."""

from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import httpx2
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from .auth import issue_token, validate_secret
from .context import CallContext
from .data.queries import QUERIES
from .data.service import SourceError
from .docs.service import INPUTS as DOCS_INPUTS

ALLOWED_HOSTS = {"localhost", "127.0.0.1", "gaia-mcp"}


def validate_source_url(url: str) -> None:
    parsed = urlsplit(url)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in ALLOWED_HOSTS:
        raise ValueError("MCP source must use an approved internal host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("MCP source URL must not contain credentials or query parameters")


def tool_scope(source: str, name: str) -> str:
    if source == "docs" and name in DOCS_INPUTS:
        return "docs.read"
    if source == "data" and name in QUERIES:
        return QUERIES[name].scope
    raise SourceError("INVALID_ARGUMENT")


class WikiMCPClient:
    def __init__(self, docs_url: str | None, data_url: str, secret: str):
        validate_secret(secret)
        validate_source_url(data_url)
        self.urls = {"data": data_url}
        if docs_url is not None:
            validate_source_url(docs_url)
            self.urls["docs"] = docs_url
        self.secret = secret

    @asynccontextmanager
    async def session(self, source: str, context: CallContext):
        if source not in self.urls:
            raise SourceError("PERMISSION_DENIED")
        token = issue_token(self.secret, context)
        async with httpx2.AsyncClient(
            headers={"Authorization": f"Bearer {token}"}, timeout=httpx2.Timeout(30)
        ) as client:
            async with streamable_http_client(self.urls[source], http_client=client) as (
                read,
                write,
            ):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    yield session

    async def list_tools(self, context: CallContext) -> list[dict]:
        tools = []
        for source in ("docs", "data"):
            if source not in self.urls:
                continue
            async with self.session(source, context) as session:
                discovered = await session.list_tools()
                for tool in discovered.tools:
                    scope = tool_scope(source, tool.name)
                    if scope in context.scopes:
                        tools.append(
                            {
                                "name": f"{source}__{tool.name}",
                                "source": source,
                                "description": tool.description,
                                "input_schema": tool.input_schema,
                            }
                        )
        return tools

    async def call_tool(self, name: str, arguments: dict, context: CallContext) -> dict:
        parts = name.split("__")
        if len(parts) != 2:
            raise SourceError("INVALID_ARGUMENT")
        source, tool = parts
        scope = tool_scope(source, tool)
        if source not in self.urls:
            raise SourceError("PERMISSION_DENIED")
        if scope not in context.scopes:
            raise SourceError("PERMISSION_DENIED")
        async with self.session(source, context) as session:
            result = await session.call_tool(tool, arguments)
            if result.structured_content is None:
                raise SourceError("INVALID_ARGUMENT" if result.is_error else "INTERNAL_ERROR")
            response = result.structured_content
            expected_source = "gaia_docs" if source == "docs" else "gaia_synthetic_db"
            if response.get("source") != expected_source or response.get("tool") != tool:
                raise SourceError("INTERNAL_ERROR")
            return response
