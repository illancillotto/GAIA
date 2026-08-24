from __future__ import annotations

from datetime import date
import logging
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.modules.catasto.services import ade_document_audit as audit_module
from app.modules.catasto.services.ade_document_audit import (
    apply_document_audit,
    audit_downloaded_document,
    audit_visura_pdf,
    expected_document_request_type,
)


def _current_text(title: str = "Visura attuale per immobile") -> str:
    return (
        f"{title}\nComune di MARRUBIU (E972)\n"
        "Foglio: 27 Particella: 604\n"
        "Situazione dell'unita immobiliare dal 01/01/2020\n"
        "Nella variazione sono stati soppressi i seguenti immobili Foglio 27 Particella 603\n"
    )


@pytest.mark.parametrize(
    ("expected", "title", "observed", "matches"),
    [
        (None, "Visura attuale per immobile", "ATTUALITA", True),
        ("STORICA", "Visura storica per immobile", "STORICA", True),
        ("STORICA", "Documento catastale", None, None),
    ],
)
def test_audit_visura_pdf_detects_requested_and_observed_type(
    monkeypatch, expected, title, observed, matches
) -> None:
    monkeypatch.setattr(audit_module, "extract_pdf_text", lambda _path: _current_text(title))

    payload = audit_visura_pdf(Path("document.pdf"), expected)

    assert payload["classification"] == "current"
    assert payload["document_request_type"] == {
        "expected": "STORICA" if expected == "STORICA" else "ATTUALITA",
        "observed": observed,
        "matches": matches,
    }


def test_audit_downloaded_document_is_fail_open_and_logs(monkeypatch, caplog) -> None:
    request = SimpleNamespace(id=uuid4(), search_mode="immobile", request_type="storica", tipo_visura="Completa")
    result = SimpleNamespace(status="completed", file_path=Path("broken.pdf"))
    monkeypatch.setattr(audit_module, "audit_visura_pdf", lambda *_args: (_ for _ in ()).throw(ValueError("bad pdf")))

    payload = audit_downloaded_document(request, result)

    assert payload == {
        "source": "ade_visura_pdf_audit",
        "classification": "parse_failed",
        "error": "bad pdf",
        "document_request_type": {"expected": "STORICA", "observed": None, "matches": None},
    }
    assert "Audit visura PDF non riuscito" in caplog.text


@pytest.mark.parametrize(
    ("search_mode", "status", "file_path"),
    [("soggetto", "completed", Path("x.pdf")), ("immobile", "failed", Path("x.pdf")), ("immobile", "completed", None)],
)
def test_audit_downloaded_document_ignores_non_pdf_flows(search_mode, status, file_path) -> None:
    request = SimpleNamespace(id=uuid4(), search_mode=search_mode, request_type=None, tipo_visura="Completa")
    result = SimpleNamespace(status=status, file_path=file_path)
    assert audit_downloaded_document(request, result) is None


def test_audit_downloaded_document_logs_normal_and_anomalous_results(monkeypatch, caplog) -> None:
    caplog.set_level(logging.INFO, logger=audit_module.__name__)
    request = SimpleNamespace(id=uuid4(), search_mode="immobile", request_type=None, tipo_visura="Completa")
    result = SimpleNamespace(status="completed", file_path=Path("visura.pdf"))
    payload = {
        "classification": "current",
        "document_request_type": {"expected": "ATTUALITA", "observed": "ATTUALITA"},
    }
    monkeypatch.setattr(audit_module, "audit_visura_pdf", lambda *_args: payload)
    assert audit_downloaded_document(request, result) is payload
    assert "classificazione=current" in caplog.text

    caplog.clear()
    payload["classification"] = "suppressed"
    payload["document_request_type"]["observed"] = "STORICA"
    assert audit_downloaded_document(request, result) is payload
    assert "classificazione=suppressed" in caplog.text


def test_apply_document_audit_maps_metadata_and_suppression_date() -> None:
    document = SimpleNamespace()
    payload = {
        "classification": "suppressed",
        "document_request_type": {"observed": "STORICA"},
        "suppression": {"suppressed_from": "09/12/2025"},
    }
    apply_document_audit(document, payload)
    assert document.content_request_type == "STORICA"
    assert document.parcel_classification == "suppressed"
    assert document.parcel_suppressed_at == date(2025, 12, 9)
    assert document.content_metadata_json is payload

    apply_document_audit(document, {"classification": None, "suppression": {"suppressed_from": "invalid"}})
    assert document.content_request_type is None
    assert document.parcel_classification == "unknown"
    assert document.parcel_suppressed_at is None

    apply_document_audit(document, {"suppression": {"suppressed_from": 123}})
    apply_document_audit(document, None)
    assert document.parcel_suppressed_at is None


@pytest.mark.parametrize(
    ("request_type", "tipo_visura", "expected"),
    [
        ("ATTUALITA", "Sintetica", "ATTUALITA"),
        (None, "Storica Analitica", "STORICA"),
        (None, "Sintetica", "STORICA"),
        (None, "Analitica", "STORICA"),
        (None, "Completa", "ATTUALITA"),
    ],
)
def test_expected_document_request_type_prefers_explicit_value(request_type, tipo_visura, expected) -> None:
    assert expected_document_request_type(request_type, tipo_visura) == expected
