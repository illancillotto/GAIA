"""Offline HAR inventory: never replay requests or export credentials/payloads."""

import hashlib
import hmac
import json
import secrets
from urllib.parse import urlsplit

HOSTS = frozenset({"www.posta-online.it", "idp-business.poste.it", "corrispondenza.poste.it"})
KNOWN_PATHS = frozenset(
    {
        "/",
        "/jod-idp-business/cas/login.html",
        "/col/archivio.do",
        "/col/gestioneListeContatti.do",
        "/col/dettaglio.do",
    }
)
METHODS = frozenset({"GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"})
MIME_TYPES = frozenset(
    {
        "application/json",
        "text/html",
        "application/pdf",
        "application/octet-stream",
        "application/x-www-form-urlencoded",
        "multipart/form-data",
        "text/plain",
    }
)


def _media_type(value) -> str:
    media = str(value or "").split(";", 1)[0].strip().lower()
    return media if media in MIME_TYPES else "other"


def _endpoint(url: str, reviewed_paths: frozenset[str], salt: bytes):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or parsed.hostname not in HOSTS:
        return None
    if parsed.username or parsed.password or parsed.port not in {None, 443}:
        return None
    # Unknown paths can embed tax codes, filenames and tokens. Retain only a
    # per-report HMAC until an operator explicitly reviews the literal path.
    identity = f"{parsed.hostname}{parsed.path}".encode()
    known = parsed.path in KNOWN_PATHS or parsed.path in reviewed_paths
    return {
        "host": parsed.hostname,
        "path": parsed.path if known else "[review-required]",
        "endpoint_id": hmac.new(salt, identity, hashlib.sha256).hexdigest(),
        "path_review_required": not known,
    }


def _observation(entry: dict, reviewed_paths: frozenset[str], salt: bytes):
    request, response = entry["request"], entry["response"]
    endpoint = _endpoint(request["url"], reviewed_paths, salt)
    if endpoint is None:
        return None
    method = request["method"]
    status = response["status"]
    if method not in METHODS or type(status) is not int or not 0 <= status <= 599:
        raise ValueError("Metodo o stato HTTP HAR non valido")
    return {
        **endpoint,
        "method": method,
        "status": status,
        "request_media_type": _media_type(request.get("postData", {}).get("mimeType")),
        "response_media_type": _media_type(response.get("content", {}).get("mimeType")),
        "operation": "unclassified",
    }


def inventory_har(content: bytes, *, reviewed_paths: frozenset[str] = frozenset()) -> dict:
    """Produce minimal observations. A capture is evidence, not an API contract."""
    if len(content) > 32 * 1024 * 1024:
        raise ValueError("HAR oltre il limite di 32 MiB")
    salt = secrets.token_bytes(32)
    try:
        entries = json.loads(content)["log"]["entries"]
        if not isinstance(entries, list) or len(entries) > 20000:
            raise ValueError("Lista HAR non valida o oltre 20000 richieste")
        observations = [_observation(entry, reviewed_paths, salt) for entry in entries]
    except (KeyError, TypeError, AttributeError, UnicodeError, ValueError, RecursionError):
        # Do not echo parser errors: malformed URLs/JSON can contain secrets.
        raise ValueError("HAR non valido: nessun dettaglio sensibile esportato") from None
    return {
        "schema_version": 1,
        "submission_enabled": False,
        "observations": [item for item in observations if item is not None],
        "ignored_entries": sum(item is None for item in observations),
        "omitted": ["headers", "cookies", "query", "bodies", "field_names", "timestamps"],
    }
