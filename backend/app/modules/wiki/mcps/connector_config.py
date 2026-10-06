"""Explicit opt-in settings for the isolated synthetic connector listener."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit

from mcp.shared.auth import OAuthClientInformationFull

from .auth import SCOPES
from .oauth_policy import OAuthPolicy
from .oauth_provider import https_url

OAUTH_PATH = "/api/wiki/mcp/connector/oauth"
DATA_PATH = "/api/wiki/mcp/connector/data"


def approved_client(item):
    client = OAuthClientInformationFull.model_validate(item)
    if not client.client_id or client.client_secret or not client.scope:
        raise ValueError("Public client identity and explicit scopes required")
    if not set(client.scope.split()) <= SCOPES.keys():
        raise ValueError("Only data scopes may be delegated")
    if set(client.grant_types) != {"authorization_code", "refresh_token"} or set(
        client.response_types
    ) != {"code"}:
        raise ValueError("Only code and refresh PKCE clients may be approved")
    return client


@dataclass(frozen=True)
class ConnectorConfig:
    issuer: str
    resource: str
    consent_url: str
    clients_file: Path
    oauth_database: Path
    data_database: Path
    audit_database: Path
    requests_per_minute: int = 60
    tools_per_minute: int = 20
    oauth_policy: OAuthPolicy = field(default_factory=OAuthPolicy)

    def __post_init__(self):
        issuer = urlsplit(https_url(self.issuer))
        resource = urlsplit(https_url(self.resource))
        consent = urlsplit(https_url(self.consent_url))
        if (
            issuer.path != OAUTH_PATH
            or resource.path != DATA_PATH
            or consent.path != "/mcp/consent"
        ):
            raise ValueError("Connector URLs must use the documented routes")
        if issuer.netloc != resource.netloc:
            raise ValueError("Issuer and resource must share the approved HTTPS origin")
        if not 1 <= self.tools_per_minute <= self.requests_per_minute <= 600:
            raise ValueError("Invalid principal request budgets")

    def clients(self):
        if self.clients_file.stat().st_size > 65536:
            raise ValueError("Client configuration too large")
        try:
            clients = [approved_client(item) for item in json.loads(self.clients_file.read_text())]
        except (ValueError, TypeError):
            raise ValueError("Invalid approved clients configuration") from None
        approved = {client.client_id: client for client in clients}
        if not approved or len(approved) != len(clients):
            raise ValueError("Unique preapproved clients required")
        return approved


def configuration(environ):
    enabled = environ.get("GAIA_MCP_OAUTH_ENABLED", "false")
    if enabled == "false":
        return None
    if enabled != "true":
        raise ValueError("GAIA_MCP_OAUTH_ENABLED must be true or false")
    prefix = "GAIA_MCP_OAUTH_"
    return ConnectorConfig(
        issuer=environ[prefix + "ISSUER"],
        resource=environ[prefix + "RESOURCE"],
        consent_url=environ[prefix + "CONSENT_URL"],
        clients_file=Path(environ[prefix + "CLIENTS_FILE"]),
        oauth_database=Path(environ[prefix + "DATABASE"]),
        data_database=Path(environ["GAIA_MCP_CONNECTOR_DATA_DATABASE"]),
        audit_database=Path(environ["GAIA_MCP_CONNECTOR_AUDIT_DATABASE"]),
        requests_per_minute=int(environ.get("GAIA_MCP_CONNECTOR_REQUESTS_PER_MINUTE", "60")),
        tools_per_minute=int(environ.get("GAIA_MCP_CONNECTOR_TOOLS_PER_MINUTE", "20")),
        oauth_policy=OAuthPolicy.from_environment(environ),
    )
