from __future__ import annotations

from datetime import date, datetime
import logging
from pathlib import Path
import re
from typing import Any

from app.modules.catasto.services.ade_historical_visura_parser import (
    extract_pdf_text,
    parse_historical_visura_text,
)


logger = logging.getLogger(__name__)


def audit_visura_pdf(file_path: Path, expected_request_type: str | None) -> dict[str, object]:
    text = extract_pdf_text(file_path)
    payload = parse_historical_visura_text(text)
    expected = _normalize_request_type(expected_request_type)
    observed = _detect_document_request_type(text)
    payload["document_request_type"] = {
        "expected": expected,
        "observed": observed,
        "matches": observed == expected if observed is not None else None,
    }
    return payload


def audit_downloaded_document(request: Any, result: Any) -> dict[str, object] | None:
    file_path = getattr(result, "file_path", None)
    if request.search_mode != "immobile" or result.status != "completed" or file_path is None:
        return None
    expected_request_type = expected_document_request_type(
        getattr(request, "request_type", None),
        getattr(request, "tipo_visura", None),
    )
    try:
        payload = audit_visura_pdf(file_path, expected_request_type)
    except Exception as exc:
        logger.warning(
            "Audit visura PDF non riuscito: request_id=%s file=%s",
            request.id,
            file_path.name,
            exc_info=True,
        )
        return {
            "source": "ade_visura_pdf_audit",
            "classification": "parse_failed",
            "error": str(exc),
            "document_request_type": {
                "expected": expected_request_type,
                "observed": None,
                "matches": None,
            },
        }
    _log_document_audit(request, file_path, payload)
    return payload


def expected_document_request_type(request_type: str | None, tipo_visura: str | None) -> str:
    if request_type:
        return _normalize_request_type(request_type)
    normalized_visura = (tipo_visura or "").strip().casefold()
    return "STORICA" if any(label in normalized_visura for label in ("storica", "sintetica", "analitica")) else "ATTUALITA"


def apply_document_audit(document: Any, payload: dict[str, object] | None) -> None:
    if not isinstance(payload, dict):
        return
    request_type = payload.get("document_request_type")
    suppression = payload.get("suppression")
    document.content_request_type = (
        str(request_type.get("observed"))
        if isinstance(request_type, dict) and request_type.get("observed")
        else None
    )
    document.parcel_classification = str(payload.get("classification") or "unknown")
    document.parcel_suppressed_at = _parse_italian_date(
        suppression.get("suppressed_from") if isinstance(suppression, dict) else None
    )
    document.content_metadata_json = payload


def _normalize_request_type(value: str | None) -> str:
    return "STORICA" if (value or "").strip().upper() == "STORICA" else "ATTUALITA"


def _detect_document_request_type(text: str) -> str | None:
    normalized = re.sub(r"\s+", " ", text).casefold()
    if "visura storica per immobile" in normalized:
        return "STORICA"
    if "visura attuale per immobile" in normalized:
        return "ATTUALITA"
    return None


def _parse_italian_date(value: object) -> date | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError:
        return None


def _log_document_audit(request: Any, file_path: Path, payload: dict[str, object]) -> None:
    request_type = payload.get("document_request_type")
    expected = request_type.get("expected") if isinstance(request_type, dict) else None
    observed = request_type.get("observed") if isinstance(request_type, dict) else None
    classification = str(payload.get("classification") or "unknown")
    is_anomaly = classification in {"suppressed", "unknown", "parse_failed"} or expected != observed
    log = logger.warning if is_anomaly else logger.info
    log(
        "Audit visura PDF: request_id=%s classificazione=%s tipo_richiesto=%s tipo_osservato=%s file=%s",
        request.id,
        classification,
        expected,
        observed or "NON_CLASSIFICATO",
        file_path.name,
    )


__all__ = [
    "apply_document_audit",
    "audit_downloaded_document",
    "audit_visura_pdf",
    "expected_document_request_type",
]
