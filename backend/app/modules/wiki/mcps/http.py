"""Authenticated stateless HTTP for the two independent internal sources."""

from contextlib import asynccontextmanager
from contextvars import ContextVar

import jwt
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount

from .auth import validate_secret, verify_token
from .context import CallContext
from .data.server import create_server as create_data_server
from .docs.server import create_server as create_docs_server

REQUEST_CONTEXT: ContextVar[CallContext] = ContextVar("gaia_mcp_request_context")


class BearerMiddleware:
    def __init__(self, app, secret: str):
        self.app = app
        self.secret = secret

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        headers = dict(scope.get("headers", []))
        authorization = headers.get(b"authorization", b"").decode("latin-1")
        try:
            if not authorization.startswith("Bearer "):
                raise jwt.InvalidTokenError("Missing bearer token")
            context = verify_token(self.secret, authorization[7:])
        except jwt.InvalidTokenError:
            await JSONResponse(
                {"error": "UNAUTHORIZED"}, status_code=401, headers={"WWW-Authenticate": "Bearer"}
            )(scope, receive, send)
            return
        token = REQUEST_CONTEXT.set(context)
        try:
            await self.app(scope, receive, send)
        finally:
            REQUEST_CONTEXT.reset(token)


def create_http_app(docs_service, data_service, secret: str):
    validate_secret(secret)
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[
            "localhost",
            "localhost:*",
            "127.0.0.1",
            "127.0.0.1:*",
            "gaia-mcp",
            "gaia-mcp:*",
        ],
        allowed_origins=[
            "http://localhost",
            "http://localhost:*",
            "http://127.0.0.1",
            "http://127.0.0.1:*",
        ],
    )
    docs = create_docs_server(docs_service, context_factory=REQUEST_CONTEXT.get)
    docs_app = docs.streamable_http_app(
        streamable_http_path="/",
        json_response=True,
        stateless_http=True,
        max_request_body_size=65536,
        transport_security=security,
    )
    data = create_data_server(data_service, REQUEST_CONTEXT.get)
    manager = StreamableHTTPSessionManager(
        data,
        json_response=True,
        stateless=True,
        max_request_body_size=65536,
        security_settings=security,
    )

    @asynccontextmanager
    async def lifespan(_app):
        async with docs.session_manager.run(), manager.run():
            yield

    application = Starlette(
        routes=[Mount("/docs", app=docs_app), Mount("/data", app=manager.handle_request)],
        lifespan=lifespan,
    )
    return BearerMiddleware(application, secret)
