from __future__ import annotations

from typing import Any

from sister_exceptions import SisterInvalidDocumentError


def reject_unexpected_document_type(result: Any) -> None:
    payload = result.document_audit_payload
    if not isinstance(payload, dict):
        return
    request_type = payload.get("document_request_type")
    if not isinstance(request_type, dict) or "matches" not in request_type:
        return
    if request_type.get("matches") is True:
        return
    if result.file_path is not None:
        result.file_path.unlink(missing_ok=True)
    expected = request_type.get("expected") or "NON_CLASSIFICATO"
    observed = request_type.get("observed") or "NON_CLASSIFICATO"
    raise SisterInvalidDocumentError(
        f"PDF SISTER difforme: richiesto {expected}, scaricato {observed}"
    )


__all__ = ["reject_unexpected_document_type"]
