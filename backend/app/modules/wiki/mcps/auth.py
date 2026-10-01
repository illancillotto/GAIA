"""Short-lived internal credentials derived from authenticated GAIA permissions."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt

from .context import CallContext

ISSUER = "gaia-wiki"
AUDIENCE = "gaia-mcp"
SCOPES = {
    "utenze.read": ("utenze", ("utenze.subjects",)),
    "catasto.read": ("catasto", ("catasto.dashboard",)),
    "ruolo.read": ("ruolo", ("ruolo.avvisi", "ruolo.tributi.view")),
}


def validate_secret(secret: str) -> None:
    if len(secret) < 32:
        raise ValueError("MCP signing secret must contain at least 32 characters")


def effective_scopes(db, user, permission_checker) -> frozenset[str]:
    if not user.is_active:
        return frozenset()
    scopes = {"docs.read"}
    for scope, (module, sections) in SCOPES.items():
        if module in user.enabled_modules and all(
            permission_checker(db, user, section) for section in sections
        ):
            scopes.add(scope)
    return frozenset(scopes)


def issue_token(secret: str, context: CallContext) -> str:
    validate_secret(secret)
    now = datetime.now(UTC)
    claims = {
        "iss": ISSUER,
        "aud": AUDIENCE,
        "sub": context.principal,
        "iat": now,
        "exp": now + timedelta(seconds=60),
        "jti": str(uuid4()),
        "type": "gaia_mcp",
        "scopes": sorted(context.scopes),
        "conversation_id": context.conversation_id,
        "experiment_run_id": context.experiment_run_id,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def verify_token(secret: str, token: str) -> CallContext:
    validate_secret(secret)
    claims = jwt.decode(
        token,
        secret,
        algorithms=["HS256"],
        issuer=ISSUER,
        audience=AUDIENCE,
        options={"require": ["exp", "iat", "sub", "iss", "aud", "jti"]},
    )
    scopes = claims.get("scopes")
    if claims.get("type") != "gaia_mcp" or not isinstance(scopes, list):
        raise jwt.InvalidTokenError("Invalid MCP credential")
    if any(not isinstance(scope, str) or scope not in {*SCOPES, "docs.read"} for scope in scopes):
        raise jwt.InvalidTokenError("Invalid MCP scope")
    return CallContext(
        principal=claims["sub"],
        scopes=frozenset(scopes),
        conversation_id=claims.get("conversation_id"),
        experiment_run_id=claims.get("experiment_run_id"),
    )
