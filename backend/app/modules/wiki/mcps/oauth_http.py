"""Unpublished OAuth foundation; GAIA session authentication is supplied by the host."""

from mcp.server.auth.handlers.metadata import MetadataHandler
from mcp.server.auth.handlers.token import TokenHandler
from mcp.server.auth.middleware.client_auth import AuthenticationError, ClientAuthenticator
from mcp.server.auth.routes import build_metadata, cors_middleware, create_auth_routes
from mcp.server.auth.settings import ClientRegistrationOptions, RevocationOptions
from pydantic import AnyHttpUrl, BaseModel, ConfigDict, Field, ValidationError
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Route

from .auth import SCOPES
from .oauth_provider import https_url
from .oauth_store import GrantCapacityError


async def capacity_error(request, exception):
    return JSONResponse(
        {"error": "temporarily_unavailable"},
        status_code=503,
        headers={"Cache-Control": "no-store", "Retry-After": "60"},
    )


class ConsentDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    request_id: str = Field(min_length=32, max_length=128)
    allowed: bool


class OAuthHTTPHandlers:
    def __init__(self, provider, authenticate):
        self.provider = provider
        self.authenticate = authenticate
        self.client_authenticator = ClientAuthenticator(provider)
        self.token_handler = TokenHandler(provider, self.client_authenticator)

    async def revoke(self, request):
        try:
            client = await self.client_authenticator.authenticate_request(request)
        except AuthenticationError:
            return JSONResponse({"error": "invalid_client"}, status_code=401)
        form = await request.form()
        value = form.get("token")
        if not isinstance(value, str) or not value:
            return JSONResponse({"error": "invalid_request"}, status_code=400)
        credential = await self.provider.load_refresh_token(client, value)
        if credential is None:
            credential = await self.provider.load_access_token(value)
        if credential is not None and credential.client_id == client.client_id:
            await self.provider.revoke_token(credential)
        return Response(status_code=200, headers={"Cache-Control": "no-store"})

    async def token(self, request):
        form = await request.form()
        resources = form.getlist("resource")
        if resources != [self.provider.resource]:
            return JSONResponse(
                {"error": "invalid_target"},
                status_code=400,
                headers={"Cache-Control": "no-store"},
            )
        return await self.token_handler.handle(request)

    async def consent(self, request):
        authorization = request.headers.get("authorization", "")
        if not authorization.startswith("Bearer "):
            return JSONResponse({"error": "UNAUTHORIZED"}, status_code=401)
        subject = await self.authenticate(authorization[7:])
        if subject is None:
            return JSONResponse({"error": "UNAUTHORIZED"}, status_code=401)
        try:
            if request.method == "GET":
                result = self.provider.consent_details(request.query_params.get("request_id", ""))
            else:
                decision = ConsentDecision.model_validate(await request.json())
                result = {
                    "redirect_url": self.provider.consent(
                        decision.request_id,
                        subject,
                        decision.allowed,
                    )
                }
        except (ValueError, ValidationError):
            return JSONResponse({"error": "INVALID_CONSENT"}, status_code=400)
        return JSONResponse(result, headers={"Cache-Control": "no-store"})


def create_oauth_app(provider, issuer, authenticate):
    issuer_url = AnyHttpUrl(https_url(issuer))
    registration = ClientRegistrationOptions(enabled=False, valid_scopes=sorted(SCOPES))
    revocation = RevocationOptions(enabled=True)
    routes = create_auth_routes(
        provider,
        issuer_url,
        client_registration_options=registration,
        revocation_options=revocation,
    )
    metadata = build_metadata(issuer_url, None, registration, revocation)
    metadata.token_endpoint_auth_methods_supported = ["none"]
    metadata.revocation_endpoint_auth_methods_supported = ["none"]
    handlers = OAuthHTTPHandlers(provider, authenticate)
    for index, route in enumerate(routes):
        if route.path == "/token":
            routes[index] = Route(
                "/token",
                cors_middleware(handlers.token, ["POST", "OPTIONS"]),
                methods=["POST", "OPTIONS"],
            )
        elif route.path == "/.well-known/oauth-authorization-server":
            routes[index] = Route(route.path, MetadataHandler(metadata).handle)
        elif route.path == "/revoke":
            routes[index] = Route(
                "/revoke",
                cors_middleware(handlers.revoke, ["POST", "OPTIONS"]),
                methods=["POST", "OPTIONS"],
            )
    routes.append(Route("/consent", handlers.consent, methods=["GET", "POST"]))
    return Starlette(routes=routes, exception_handlers={GrantCapacityError: capacity_error})
