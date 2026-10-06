"""Opt-in OAuth connector exposing only synthetic Data MCP, never Docs/inspection."""

import json
import logging
import os
import sqlite3
from contextlib import AsyncExitStack, asynccontextmanager
from urllib.parse import urlsplit

from mcp.server.auth.routes import cors_middleware, create_protected_resource_routes
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Mount, Route

from .audit import AuditStore
from .auth import SCOPES
from .connector_budget import PrincipalBudget
from .connector_config import configuration
from .context import CallContext
from .data.database import dataset_manifest
from .data.generator import generate_dataset
from .data.server import create_server
from .data.service import DataService
from .docs.cli import EventFormatter
from .http import REQUEST_CONTEXT
from .oauth_admin import admin_route
from .oauth_gaia import gaia_oauth_callbacks
from .oauth_http import create_oauth_app
from .oauth_maintenance import maintenance
from .oauth_provider import GAIAOAuthProvider
from .oauth_store import OAuthStore, token_hash

logger = logging.getLogger(__name__)
MAX_BODY = 65536


async def read_body(receive):
    body = bytearray()
    while True:
        message = await receive()
        if message["type"] == "http.disconnect":
            raise ValueError("Disconnected request")
        body.extend(message.get("body", b""))
        if len(body) > MAX_BODY:
            raise ValueError("Request too large")
        if not message.get("more_body", False):
            return bytes(body)


class ConnectorBearer:
    def __init__(self, app, provider, budget, metadata_url):
        self.app = app
        self.provider = provider
        self.budget = budget
        self.metadata_url = metadata_url

    async def __call__(self, scope, receive, send):
        authorization = dict(scope.get("headers", [])).get(b"authorization", b"").decode("latin-1")
        credential = None
        if authorization.startswith("Bearer "):
            credential = await self.provider.load_access_token(authorization[7:])
        if credential is None or not credential.subject:
            await JSONResponse(
                {"error": "UNAUTHORIZED"},
                status_code=401,
                headers={
                    "WWW-Authenticate": f'Bearer resource_metadata="{self.metadata_url}"',
                },
            )(scope, receive, send)
            return
        try:
            body = await read_body(receive)
            payload = json.loads(body) if body else {}
            if not isinstance(payload, dict):
                raise ValueError("JSON-RPC batches are not supported")
        except (ValueError, TypeError):
            await JSONResponse({"error": "INVALID_REQUEST"}, status_code=400)(scope, receive, send)
            return
        context = CallContext(
            f"gaia:{credential.subject}", frozenset(set(credential.scopes) & SCOPES.keys())
        )
        try:
            allowed = self.budget.admit(context.principal, payload.get("method") == "tools/call")
        except sqlite3.Error:
            await JSONResponse({"error": "CONNECTOR_UNAVAILABLE"}, status_code=503)(
                scope, receive, send
            )
            return
        if not allowed:
            logger.info(
                "gaia_mcp_connector_budget_denied",
                extra={
                    "mcp_event": {
                        "principal": token_hash(context.principal),
                        "request_id": context.request_id,
                        "status": "error",
                        "error": {"code": "PRINCIPAL_BUDGET_EXCEEDED"},
                    }
                },
            )
            await JSONResponse(
                {"error": "PRINCIPAL_BUDGET_EXCEEDED"},
                status_code=429,
                headers={"Retry-After": "60"},
            )(scope, receive, send)
            return
        replayed = False

        async def buffered_receive():
            nonlocal replayed
            if replayed:
                return await receive()
            replayed = True
            return {"type": "http.request", "body": body, "more_body": False}

        token = REQUEST_CONTEXT.set(context)
        try:
            await self.app(scope, buffered_receive, send)
        finally:
            REQUEST_CONTEXT.reset(token)


def connector_routes(config, provider, authenticate, manager, budget):
    issuer_path = urlsplit(config.issuer).path
    resource_path = urlsplit(config.resource).path
    origin = config.resource.removesuffix(resource_path)
    metadata_path = "/.well-known/oauth-protected-resource" + resource_path
    auth = create_oauth_app(provider, config.issuer, authenticate)
    auth_metadata = next(
        route for route in auth.routes if route.path == "/.well-known/oauth-authorization-server"
    )
    routes = create_protected_resource_routes(
        AnyHttpUrl(config.resource),
        [AnyHttpUrl(config.issuer)],
        scopes_supported=sorted(SCOPES),
        resource_name="GAIA Synthetic Data MCP",
    )
    routes.extend(
        [
            Route(
                "/.well-known/oauth-authorization-server" + issuer_path,
                cors_middleware(auth_metadata.endpoint, ["GET", "OPTIONS"]),
                methods=["GET", "OPTIONS"],
            ),
            Mount(issuer_path, app=auth),
            Route(
                resource_path,
                ConnectorBearer(manager.handle_request, provider, budget, origin + metadata_path),
                methods=["GET", "POST", "DELETE"],
            ),
        ]
    )
    return routes


def connector_manager(config, service):
    origins = {
        config.resource.removesuffix(urlsplit(config.resource).path),
        config.consent_url.removesuffix("/mcp/consent"),
    }
    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=sorted({urlsplit(origin).netloc for origin in origins}),
        allowed_origins=sorted(origins),
    )
    return StreamableHTTPSessionManager(
        create_server(service, REQUEST_CONTEXT.get),
        json_response=True,
        stateless=True,
        max_request_body_size=MAX_BODY,
        security_settings=security,
    )


def create_connector_app(config, session_factory):
    if config is None:
        return Starlette()
    application = Starlette()

    @asynccontextmanager
    async def lifespan(_app):
        async with AsyncExitStack() as stack:
            store = OAuthStore(config.oauth_database, policy=config.oauth_policy)
            stack.callback(store.close)
            audit = AuditStore(config.audit_database)
            stack.callback(audit.close)
            service = DataService(config.data_database, audit=audit)
            stack.callback(service.close)
            expected = dataset_manifest(
                service.manifest["seed"], generate_dataset(service.manifest["seed"])
            )
            if service.manifest != expected:
                raise ValueError("Connector requires an unmodified generated synthetic dataset")
            user_scopes, authenticate = gaia_oauth_callbacks(session_factory)
            provider = GAIAOAuthProvider(
                store,
                config.clients(),
                user_scopes,
                resource=config.resource,
                consent_url=config.consent_url,
            )
            manager = connector_manager(config, service)
            budget = PrincipalBudget(store, config.requests_per_minute, config.tools_per_minute)
            await stack.enter_async_context(maintenance(store, budget))
            application.router.routes = connector_routes(
                config, provider, authenticate, manager, budget
            )
            application.router.routes.insert(
                0, admin_route(urlsplit(config.issuer).path, store, session_factory)
            )
            try:
                async with manager.run():
                    yield
            finally:
                application.router.routes = []

    application.router.lifespan_context = lifespan
    return application


def create_configured_app():
    config = configuration(os.environ)
    if config is None:
        return create_connector_app(None, None)
    from app.core.database import SessionLocal

    event_logger = logging.getLogger("app.modules.wiki.mcps")
    handler = logging.StreamHandler()
    handler.setFormatter(EventFormatter())
    event_logger.handlers = [handler]
    event_logger.setLevel(logging.INFO)
    event_logger.propagate = False

    return create_connector_app(config, SessionLocal)
