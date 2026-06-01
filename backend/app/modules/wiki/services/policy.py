from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy.orm import Session

from app.models.application_user import ApplicationUser
from app.modules.wiki.schemas import WikiChatResponse, WikiEvidence
from app.services.permission_resolver import can_access_section

_SENSITIVE_PAYLOAD_KEYS = {
    "email",
    "password",
    "password_hash",
    "token",
    "access_token",
    "refresh_token",
    "secret",
    "error_detail",
    "params_json",
    "payload_json",
    "text_note",
    "review_note",
    "notes",
    "admin_notes",
    "agent_response",
    "email",
    "path",
    "geojson",
    "geometry",
    "shape_wkt",
    "wkt",
    "coordinates",
    "coordinate",
    "lat",
    "lng",
    "latitude",
    "longitude",
}
_MAX_INLINE_STRING_LENGTH = 280
_MAX_COLLECTION_ITEMS = 5


@dataclass(frozen=True)
class WikiToolMeta:
    name: str
    module_key: str | None = None
    required_sections: tuple[str, ...] = field(default_factory=tuple)
    allowed_roles: tuple[str, ...] | None = None
    redacted_payload_keys: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class WikiToolAccessDecision:
    allowed: bool
    reason_code: str | None = None
    reason_message: str | None = None


def evaluate_tool_access(db: Session, current_user: ApplicationUser, meta: WikiToolMeta) -> WikiToolAccessDecision:
    if meta.allowed_roles and current_user.role not in meta.allowed_roles and not current_user.is_super_admin:
        return WikiToolAccessDecision(
            allowed=False,
            reason_code="role_denied",
            reason_message="Il tuo ruolo non può eseguire questo tipo di interrogazione.",
        )

    if meta.module_key and meta.module_key not in current_user.enabled_modules and not current_user.is_super_admin:
        return WikiToolAccessDecision(
            allowed=False,
            reason_code="module_denied",
            reason_message="Non posso accedere a questi dati con i permessi del tuo account: il modulo richiesto non è abilitato.",
        )

    for section_key in meta.required_sections:
        if not can_access_section(db, current_user, section_key):
            return WikiToolAccessDecision(
                allowed=False,
                reason_code="section_denied",
                reason_message=f"Il tuo account non ha accesso alla sezione richiesta: {section_key}.",
            )

    return WikiToolAccessDecision(allowed=True)


def is_tool_allowed(db: Session, current_user: ApplicationUser, meta: WikiToolMeta) -> bool:
    return evaluate_tool_access(db, current_user, meta).allowed


def _sanitize_payload_value(value: Any, *, redacted_keys: set[str]) -> Any:
    if isinstance(value, dict):
        sanitized: dict[str, Any] = {}
        for key, nested_value in value.items():
            if key in redacted_keys:
                continue
            sanitized[key] = _sanitize_payload_value(nested_value, redacted_keys=redacted_keys)
        return sanitized
    if isinstance(value, list):
        return [_sanitize_payload_value(item, redacted_keys=redacted_keys) for item in value[:_MAX_COLLECTION_ITEMS]]
    if isinstance(value, str) and len(value) > _MAX_INLINE_STRING_LENGTH:
        return f"{value[:_MAX_INLINE_STRING_LENGTH]}..."
    return value


def sanitize_wiki_response(meta: WikiToolMeta, response: WikiChatResponse) -> WikiChatResponse:
    redacted_keys = _SENSITIVE_PAYLOAD_KEYS | set(meta.redacted_payload_keys)
    if not redacted_keys:
        return response

    sanitized_evidences: list[WikiEvidence] = []
    for evidence in response.evidences:
        sanitized_evidences.append(
            evidence.model_copy(
                update={
                    "payload": _sanitize_payload_value(evidence.payload, redacted_keys=redacted_keys)
                    if evidence.payload is not None
                    else None,
                }
            )
        )
    return response.model_copy(update={"evidences": sanitized_evidences})
