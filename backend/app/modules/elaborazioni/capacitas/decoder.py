from __future__ import annotations

import base64
import logging
from urllib.parse import unquote
import zlib

import json5

logger = logging.getLogger(__name__)


def decode_response(payload: str) -> list | dict | str:
    if payload.startswith("NO"):
        error_message = unquote(payload[2:].replace("+", " "))
        raise ValueError(f"Errore applicativo Capacitas: {error_message}")

    if payload.startswith("SI") or payload.startswith("OK"):
        return payload[2:]

    if payload.startswith("SZ"):
        payload = payload[2:]

    padded = payload + "=" * (-len(payload) % 4)
    try:
        raw_bytes = base64.b64decode(padded)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Base64 decode fallito: {exc}") from exc

    try:
        inflated = zlib.decompress(raw_bytes, -15)
    except zlib.error as exc:
        raise ValueError(
            f"Raw deflate inflate fallito: {exc}. Primi 20 bytes hex: {raw_bytes[:20].hex()}",
        ) from exc

    try:
        text = inflated.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = inflated.decode("latin-1")

    logger.debug(
        "Capacitas decoder: %d bytes -> %d chars | preview: %s...",
        len(inflated),
        len(text),
        text[:80].replace("\n", " "),
    )

    try:
        return json5.loads(text)
    except Exception as exc:
        raise ValueError(
            f"json5 parse fallito: {exc}. Testo (primi 200 chars): {text[:200]}",
        ) from exc


def is_sz_response(payload: str) -> bool:
    return payload.startswith("SZ")
