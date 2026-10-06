"""Internal-only administrative revocation using canonical GAIA roles."""

import logging
import sqlite3

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.responses import JSONResponse
from starlette.routing import Route

from app.api.deps import require_active_user, require_role
from app.services.auth import get_current_user_from_token

from .oauth_store import token_hash

logger = logging.getLogger(__name__)
admin_role = require_role("super_admin", "admin")


class RevocationSelector(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    subject: str | None = Field(default=None, min_length=1, max_length=128)
    client_id: str | None = Field(default=None, min_length=1, max_length=256)

    @model_validator(mode="after")
    def explicit_selector(self):
        if self.subject is None and self.client_id is None:
            raise ValueError("Explicit revocation selector required")
        return self


class AdminRevocation:
    def __init__(self, store, session_factory):
        self.store = store
        self.session_factory = session_factory

    def administrator(self, authorization):
        if not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401)
        with self.session_factory() as database:
            user = get_current_user_from_token(database, authorization[7:])
            return str(admin_role(require_active_user(user)).id)

    async def __call__(self, request):
        try:
            actor = self.administrator(request.headers.get("authorization", ""))
        except HTTPException as exception:
            return JSONResponse({"error": "ADMIN_REQUIRED"}, status_code=exception.status_code)
        try:
            selector = RevocationSelector.model_validate(await request.json())
        except ValueError:
            return JSONResponse({"error": "INVALID_SELECTOR"}, status_code=400)
        try:
            revoked = self.store.revoke_authorizations(**selector.model_dump())
        except sqlite3.Error:
            return JSONResponse({"error": "CONNECTOR_UNAVAILABLE"}, status_code=503)
        logger.info(
            "gaia_mcp_oauth_admin_revocation",
            extra={
                "mcp_event": {
                    "principal": token_hash(actor),
                    "status": "ok",
                    "revoked_grants": revoked,
                    "selectors": {
                        key: token_hash(value)
                        for key, value in selector.model_dump(exclude_none=True).items()
                    },
                }
            },
        )
        return JSONResponse({"revoked_grants": revoked}, headers={"Cache-Control": "no-store"})


def admin_route(path, store, session_factory):
    handler = AdminRevocation(store, session_factory)
    return Route(path + "/admin/revoke", handler.__call__, methods=["POST"])
