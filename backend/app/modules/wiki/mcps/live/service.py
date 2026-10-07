"""Read-only tools with fresh GAIA authorization and metadata-only audit."""

import hashlib
from collections import deque
from datetime import UTC, datetime
from time import monotonic
from uuid import uuid4

from pydantic import ValidationError

from .api import SourceError
from .catalog import TOOLS


def project(value, fields, depth=0):
    if depth > 6:
        return None, True
    if isinstance(value, dict):
        output = {}
        truncated = False
        for key in value.keys() & fields:
            output[key], cut = project(value[key], fields, depth + 1)
            truncated |= cut
        return output, truncated
    if isinstance(value, list):
        values = [project(item, fields, depth + 1) for item in value[:50]]
        return [item for item, cut in values], len(value) > 50 or any(cut for item, cut in values)
    if isinstance(value, str):
        return value[:500], len(value) > 500
    return value, False


class LiveService:
    def __init__(self, api, audit, approved_tools):
        if not approved_tools or not set(approved_tools) <= TOOLS.keys():
            raise ValueError("Explicit nonempty tool allowlist required")
        self.api = api
        self.audit = audit
        self.approved_tools = frozenset(approved_tools)
        self.requests = deque()

    def admit(self, tool_call):
        now = monotonic()
        while self.requests and self.requests[0][0] <= now - 60:
            self.requests.popleft()
        if len(self.requests) >= 60 or (tool_call and sum(item[1] for item in self.requests) >= 20):
            raise SourceError("RATE_LIMITED")
        self.requests.append((now, tool_call))

    async def identity(self):
        user = await self.api.get("/api/auth/me")
        permissions = await self.api.get("/api/auth/my-permissions")
        if (
            not isinstance(user, dict)
            or user.get("is_active") is not True
            or type(user.get("id")) is not int
            or user["id"] <= 0
            or not isinstance(user.get("enabled_modules"), list)
            or not isinstance(permissions, dict)
            or not isinstance(permissions.get("granted_keys"), list)
        ):
            raise SourceError("AUTH_REQUIRED")
        if not all(
            isinstance(item, str) for item in user["enabled_modules"] + permissions["granted_keys"]
        ):
            raise SourceError("AUTH_REQUIRED")
        return user, permissions["granted_keys"]

    def permitted(self, name, user, sections):
        spec = TOOLS[name]
        modules = {spec.module} if spec.module else set()
        if name == "search_gaia":
            modules = {"utenze", "catasto", "ruolo"}
        return (
            name in self.approved_tools
            and modules <= set(user["enabled_modules"])
            and set(spec.sections) <= set(sections)
        )

    async def tools(self):
        self.admit(False)
        user, sections = await self.identity()
        return [name for name in TOOLS if self.permitted(name, user, sections)]

    async def call(self, name, arguments):
        principal = "unresolved"
        try:
            self.admit(True)
            if name not in TOOLS:
                raise SourceError("UNKNOWN_TOOL")
            user, sections = await self.identity()
            principal = f"gaia:{user['id']}"
            if not self.permitted(name, user, sections):
                raise SourceError("PERMISSION_DENIED")
            spec = TOOLS[name]
            params = spec.inputs.model_validate(arguments).model_dump(
                mode="json", exclude_none=True
            )
            path = "/api" + spec.path.format(record_id=params.pop("record_id", ""))
            raw = await self.api.get(path, params)
            data, truncated = project(raw, spec.fields)
            result = {
                "data": data,
                "truncated": truncated,
                "source": "gaia_live_api",
                "path": path,
                "retrieved_at": datetime.now(UTC).isoformat(),
            }
            status = "ok"
        except ValidationError:
            result = {"error": {"code": "INVALID_ARGUMENT"}}
            status = "INVALID_ARGUMENT"
        except SourceError as exc:
            status = str(exc)
            result = {"error": {"code": status}}
        event = {
            "principal": hashlib.sha256(principal.encode()).hexdigest()[:24],
            "permission_scope": "live.read",
            "dataset_or_corpus_version": "gaia-live-v1",
            "request_id": str(uuid4()),
            "tool_name": name if name in TOOLS else "unknown",
            "status": status,
        }
        try:
            self.audit.record(event, {}, {"status": status})
        except Exception:
            return {"error": {"code": "AUDIT_UNAVAILABLE"}}
        return result
