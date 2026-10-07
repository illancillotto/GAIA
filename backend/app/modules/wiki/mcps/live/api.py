"""Bounded HTTPS transport; only GAIA APIs receive the user's in-memory credential."""

import json
import ssl
from urllib.parse import urlsplit

import httpx


class SourceError(Exception):
    pass


class GaiaAPI:
    def __init__(self, origin, token, *, ca_file=None, transport=None):
        parsed = urlsplit(origin)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.path not in {"", "/"}
            or any((parsed.username, parsed.password, parsed.query, parsed.fragment))
            or not token
            or any(character in token for character in "\r\n")
        ):
            raise ValueError("Explicit HTTPS origin and valid in-memory credential required")
        self.client = httpx.AsyncClient(
            base_url=origin.rstrip("/"),
            headers={"Authorization": f"Bearer {token}"},
            verify=ssl.create_default_context(cafile=ca_file),
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=10,
        )

    async def close(self):
        await self.client.aclose()

    async def get(self, path, params=None):
        if not path.startswith("/api/") or ".." in path or "?" in path:
            raise SourceError("INVALID_SOURCE_PATH")
        try:
            async with self.client.stream("GET", path, params=params) as response:
                if response.status_code != 200:
                    raise SourceError(
                        {
                            401: "AUTH_REQUIRED",
                            403: "PERMISSION_DENIED",
                            404: "NOT_FOUND",
                            429: "RATE_LIMITED",
                        }.get(response.status_code, "SOURCE_UNAVAILABLE")
                    )
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 65536:
                        raise SourceError("SOURCE_RESPONSE_TOO_LARGE")
                value = json.loads(content)
                if not isinstance(value, dict | list | type(None)):
                    raise SourceError("INVALID_SOURCE_RESPONSE")
                return value
        except (httpx.HTTPError, ValueError, RecursionError) as exc:
            raise SourceError("SOURCE_UNAVAILABLE") from exc
