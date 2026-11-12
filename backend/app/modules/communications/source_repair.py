"""Explicit PDF revision with a unique canonical portal account; originals are retained."""

import io
import re
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from pypdf import PdfReader
from sqlalchemy import select

from app.modules.ruolo.models import RuoloTributiReminderBatchItem
from app.modules.ruolo.notice_register_models import NoticeAudit
from app.modules.ruolo.services.notice_communication_fields import template_variables
from app.modules.ruolo.services.taxpayer_portal_access import with_portal_access
from app.modules.ruolo.services.tributi_reminder_service import (
    GAIA_PROPOSAL_TEMPLATE_KEY,
    reminder_storage_dir,
)

from . import ruolo_source
from .policy import Conflict, pdf_pages, sha256


def complete_portal_snapshot(db, identity, expected_sha, actor_id):
    db.scalar(
        select(RuoloTributiReminderBatchItem)
        .where(RuoloTributiReminderBatchItem.id == identity)
        .with_for_update()
    )
    item = ruolo_source.source_item(db, identity)
    if item.status != "generated" or item.years_json != [2021]:
        raise Conflict("Revisione disponibile solo per PDF definitivi 2021")
    document = ruolo_source._document(db, item)
    db.refresh(document, with_for_update=True)
    document = ruolo_source._document(db, item)
    original = ruolo_source.read_pdf(item)
    if sha256(original) != expected_sha:
        raise Conflict("PDF cambiato: riaprire l'avviso prima della revisione")
    payload = item.payload_json or {}
    if {"codice_utenza", "pin_utenza"} <= template_variables(item).keys():
        return {"source_sha256": expected_sha}
    candidate = with_portal_access(db, [{"codice_fiscale": item.codice_fiscale}])[0]
    revised = {
        **payload,
        "taxpayer_portal_access": candidate["taxpayer_portal_access"],
        "template_path": GAIA_PROPOSAL_TEMPLATE_KEY,
    }
    fields = template_variables(
        SimpleNamespace(
            payload_json=revised,
            display_name=item.display_name,
            codice_fiscale=item.codice_fiscale,
            saldo_amount=item.saldo_amount,
            years_json=item.years_json,
        )
    )
    if not {"codice_utenza", "pin_utenza", "importo_documento"} <= fields.keys():
        raise Conflict(
            "Credenziali o importi assenti, ambigui o non validi: verifica dell'ufficio necessaria"
        )
    path, content = revised_pdf(revised, fields)
    before = {
        "document_path": item.generated_document_path,
        "payload": payload,
        "pdf_sha256": expected_sha,
    }
    item.payload_json, item.generated_document_path = revised, str(path)
    document.version += 1
    document.original_json = {
        **document.original_json,
        "payload": revised,
        "document_path": str(path),
    }
    db.add(
        NoticeAudit(
            document_id=document.id,
            version=document.version,
            actor_id=actor_id,
            action="complete_portal_snapshot",
            reason="Revisione esplicita 2021: credenziali canoniche, importi e numero salvati invariati; originale conservato",
            before_json=before,
            after_json={"document_path": str(path), "pdf_sha256": sha256(content)},
        )
    )
    db.flush()
    return {"source_sha256": sha256(content)}


def revised_pdf(payload, fields):
    path = reminder_storage_dir() / f"communication-revision-{uuid4()}.pdf"
    status, result, _ = ruolo_source.repo._generate_batch_document(payload, output_path=path)
    if status != "generated" or result != str(path):
        raise Conflict("Revisione PDF non riuscita: documento originale conservato")
    Path(result).chmod(0o600)
    content = Path(result).read_bytes()
    pdf_pages(content)
    text = " ".join(page.extract_text() or "" for page in PdfReader(io.BytesIO(content)).pages)
    required = (
        r"Codice\s+(?:ditta|utenza)\s*:\s*" + re.escape(fields["codice_utenza"]) + r"(?![0-9])",
        r"\bPIN\s*:\s*" + re.escape(fields["pin_utenza"]) + r"(?![0-9])",
        re.escape(str(payload["notice_number"])),
        re.escape(fields["importo_documento"]),
    )
    if not all(re.search(pattern, text, re.IGNORECASE) for pattern in required):
        raise Conflict(
            "Credenziali, importo o numero non verificabili nel nuovo PDF: originale conservato"
        )
    return path, content
