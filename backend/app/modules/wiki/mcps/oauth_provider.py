"""MCP SDK authorization provider delegating to current GAIA user permissions."""

from urllib.parse import urlencode, urlsplit

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizeError,
    RefreshToken,
    TokenError,
)
from mcp.shared.auth import OAuthToken

from .auth import SCOPES


def https_url(value):
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or any((parsed.username, parsed.password, parsed.query, parsed.fragment))
    ):
        raise ValueError("Explicit clean HTTPS URL required")
    return value


class GAIAOAuthProvider:
    def __init__(self, store, clients, user_scopes, *, resource, consent_url):
        self.store = store
        self.clients = clients
        self.user_scopes = user_scopes
        self.resource = https_url(resource)
        self.consent_url = https_url(consent_url)
        if not clients:
            raise ValueError("At least one preapproved client required")
        for client in clients.values():
            if client.token_endpoint_auth_method != "none" or not client.redirect_uris:
                raise ValueError("Preapproved public PKCE clients required")
            for redirect in client.redirect_uris:
                https_url(str(redirect))

    async def get_client(self, client_id):
        return self.clients.get(client_id)

    async def register_client(self, client_info):
        raise NotImplementedError("Dynamic registration disabled")

    async def authorize(self, client, params):
        scopes = params.scopes or []
        if self.clients.get(client.client_id) != client:
            raise AuthorizeError("unauthorized_client")
        if params.resource != self.resource:
            raise AuthorizeError("invalid_target")
        if not scopes or not set(scopes) <= SCOPES.keys():
            raise AuthorizeError("invalid_scope")
        if str(params.redirect_uri) not in {str(uri) for uri in client.redirect_uris}:
            raise AuthorizeError("invalid_request")
        pending = self.store.put(
            "pending",
            {"client_id": client.client_id, "params": params.model_dump(mode="json")},
            lifetime=300,
        )
        return self.consent_url + "?" + urlencode({"request_id": pending})

    def consent_details(self, request_id):
        pending = self.store.get("pending", request_id)
        if pending is None or pending["client_id"] not in self.clients:
            raise ValueError("Invalid consent request")
        client = self.clients[pending["client_id"]]
        params = pending["params"]
        if params["resource"] != self.resource or params["redirect_uri"] not in {
            str(uri) for uri in client.redirect_uris
        }:
            raise ValueError("Invalid consent request")
        return {
            "client_name": client.client_name or client.client_id,
            "scopes": pending["params"]["scopes"],
            "resource": self.resource,
            "redirect_uri": params["redirect_uri"],
        }

    def consent(self, request_id, user_id, allowed):
        self.consent_details(request_id)
        pending = self.store.consume("pending", request_id)
        if pending is None:
            raise ValueError("Invalid consent request")
        params = pending["params"]
        granted = set(params["scopes"]) & self.user_scopes(str(user_id))
        if not allowed or granted != set(params["scopes"]):
            response = {"error": "access_denied"}
        else:
            payload = {**params, "client_id": pending["client_id"], "subject": str(user_id)}
            response = {"code": self.store.put("code", payload, lifetime=60)}
        if params["state"] is not None:
            response["state"] = params["state"]
        return params["redirect_uri"] + "?" + urlencode(response)

    async def load_authorization_code(self, client, authorization_code):
        grant = self.store.get("code", authorization_code)
        if grant is None or grant["client_id"] != client.client_id:
            return None
        return AuthorizationCode(code=authorization_code, **grant)

    def current_scopes(self, grant):
        return set(grant["scopes"]) & self.user_scopes(grant["subject"]) & SCOPES.keys()

    def tokens(self, grant, scopes):
        payload = {
            "client_id": grant["client_id"],
            "subject": grant["subject"],
            "scopes": sorted(scopes),
            "resource": self.resource,
        }
        access = self.store.put("access", payload, lifetime=300, family=grant["family"])
        refresh = self.store.put("refresh", payload, lifetime=28800, family=grant["family"])
        return OAuthToken(
            access_token=access,
            refresh_token=refresh,
            token_type="Bearer",
            expires_in=300,
            scope=" ".join(sorted(scopes)),
        )

    async def exchange_authorization_code(self, client, authorization_code):
        grant = self.store.get("code", authorization_code.code)
        if grant is None or grant["client_id"] != client.client_id:
            raise TokenError("invalid_grant")
        scopes = self.current_scopes(grant)
        if not scopes:
            raise TokenError("invalid_grant")
        with self.store.transaction():
            grant = self.store.consume("code", authorization_code.code, client_id=client.client_id)
            if grant is None:
                raise TokenError("invalid_grant")
            return self.tokens(grant, scopes)

    async def load_refresh_token(self, client, refresh_token):
        reused = self.store.get("used_refresh", refresh_token)
        if reused is not None and reused["client_id"] == client.client_id:
            self.store.revoke_by_family(reused["family"])
            return None
        grant = self.store.get("refresh", refresh_token)
        if grant is None or grant["client_id"] != client.client_id:
            return None
        return RefreshToken(
            token=refresh_token, **{**grant, "expires_at": int(grant["expires_at"])}
        )

    async def exchange_refresh_token(self, client, refresh_token, scopes):
        grant = self.store.get("refresh", refresh_token.token)
        if grant is None or grant["client_id"] != client.client_id:
            raise TokenError("invalid_grant")
        requested = set(scopes)
        if not requested or not requested <= set(grant["scopes"]):
            raise TokenError("invalid_scope")
        current = requested & self.current_scopes(grant)
        if not current:
            raise TokenError("invalid_grant")
        with self.store.transaction():
            grant = self.store.consume("refresh", refresh_token.token, client_id=client.client_id)
            if grant is None:
                raise TokenError("invalid_grant")
            self.store.revoke_by_family(grant["family"])
            return self.tokens(grant, current)

    async def load_access_token(self, token):
        grant = self.store.get("access", token)
        if grant is None or grant["resource"] != self.resource:
            return None
        scopes = self.current_scopes(grant)
        if not scopes:
            return None
        return AccessToken(
            token=token,
            client_id=grant["client_id"],
            subject=grant["subject"],
            scopes=sorted(scopes),
            resource=self.resource,
            expires_at=int(grant["expires_at"]),
        )

    async def revoke_token(self, token):
        self.store.revoke(token.token)
