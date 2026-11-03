"""Pure integrity, state and configuration rules shared by HTTP and worker."""

import hashlib
import io
import json
import os
import re
from datetime import UTC, datetime

from pypdf import PdfReader

MAX_BYTES = 32 * 1024 * 1024
MAX_PAGES = 200
EDITABLE = {"draft", "ready", "approved"}
TRANSITIONS = {
    "draft": {"ready", "cancelled"},
    "ready": {"draft", "approved", "cancelled"},
    "approved": {"draft", "queued", "cancelled"},
    "queued": {"sending", "failed", "cancelled"},
    "sending": {"submitted", "failed", "uncertain", "queued"},
    "submitted": {"accepted", "delivered", "not_delivered"},
    "accepted": {"delivered", "not_delivered"},
    "uncertain": {"accepted", "delivered", "not_delivered", "submitted"},
    "not_delivered": {"delivered"},
    "delivered": set(),
    "failed": {"cancelled"},
    "cancelled": set(),
}


class Conflict(ValueError):
    """A command cannot satisfy current data, authorization or integrity."""


class Missing(LookupError):
    """A resource does not exist in the authorized scope."""


def now():
    return datetime.now(UTC)


def digest(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()


def sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def pdf_pages(content: bytes) -> int:
    if not content.startswith(b"%PDF-") or len(content) > MAX_BYTES:
        raise Conflict("PDF non valido o oltre 32 MiB")
    try:
        reader = PdfReader(io.BytesIO(content), strict=True)
        count = len(reader.pages) if not reader.is_encrypted else 0
    except Exception as exc:
        raise Conflict("PDF illeggibile") from exc
    if not 1 <= count <= MAX_PAGES:
        raise Conflict("PDF cifrato, vuoto o oltre 200 pagine")
    return count


def transport_enabled() -> bool:
    return os.environ.get("COMMUNICATIONS_TRANSPORT_ENABLED", "false").lower() == "true"


def verify_snapshots(parts, source_sha256, max_bytes, body):
    if not parts or not parts[0].primary_document or parts[0].sha256 != source_sha256:
        raise Conflict("Snapshot non coincide con il PDF definitivo")
    for part in parts:
        if sha256(part.content) != part.sha256 or len(part.content) != part.size:
            raise Conflict("Integrità dello snapshot non verificata")
    if sum(part.size * 4 // 3 + 4096 for part in parts) + len(body.encode()) > max_bytes:
        raise Conflict("Messaggio oltre il limite dimensionale dell'account")


def account_fingerprint(account) -> str:
    fields = (
        "id",
        "version",
        "channel",
        "sender",
        "display_name",
        "provider",
        "smtp_host",
        "smtp_port",
        "smtp_encryption",
        "imap_host",
        "imap_port",
        "imap_encryption",
        "auth_method",
        "username",
        "secret_ref",
        "allowed_modules",
        "allowed_user_ids",
        "max_bytes",
        "hourly_limit",
    )
    return digest({key: getattr(account, key) for key in fields})


def render_template(text: str, variables: dict) -> str:
    """Plain text only; no expression interpreter, HTML, includes or attribute access."""

    def replace(match):
        key = match.group(1)
        if key not in variables:
            raise Conflict(f"Variabile template mancante: {key}")
        return str(variables[key])

    rendered = re.sub(r"\{\{\s*([a-z_]+)\s*\}\}", replace, text)
    if any(marker in rendered for marker in ("{{", "}}", "{%", "{#")):
        raise Conflict("Sintassi template non consentita")
    return rendered


def envelope_digest(message, attachments) -> str:
    fields = (
        "source_module",
        "source_entity_id",
        "document_id",
        "notice_number",
        "channel",
        "account_id",
        "account_digest",
        "sender",
        "recipient",
        "subject",
        "body",
        "purpose",
        "template_id",
        "source_digest",
        "version",
    )
    return digest(
        {
            "message": {key: getattr(message, key) for key in fields},
            "attachments": sorted(
                (str(a.id), a.filename, a.sha256, a.size, a.version) for a in attachments
            ),
        }
    )
