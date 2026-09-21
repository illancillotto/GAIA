"""Register GAIA-generated documents in the generating transaction, not as shipments."""

from uuid import UUID, uuid4

from sqlalchemy import select

from app.modules.ruolo.models import RuoloAvviso, RuoloTributiReminderBatch
from app.modules.ruolo.notice_register_models import (
    NoticeAudit,
    NoticeDocument,
    NoticeEvidence,
    NoticeNotification,
    NoticePosition,
    NoticeRecovery,
)
from app.modules.ruolo.services.notice_drafts import retain_draft_number


def _publish(db, source: str, record, avviso_ids: list[UUID], actor_id: int):
    if actor_id is None:
        raise ValueError("Operatore obbligatorio per registrare la generazione")
    existing = db.scalar(
        select(NoticeDocument).where(
            NoticeDocument.source_system == source,
            NoticeDocument.source_key == str(record.id),
        )
    )
    if existing is not None:
        return existing
    avvisi = list(
        db.scalars(
            select(RuoloAvviso).where(RuoloAvviso.id.in_(avviso_ids)).order_by(RuoloAvviso.id)
        ).all()
    )
    if not avvisi or len(avvisi) != len(set(avviso_ids)):
        raise ValueError("Posizioni GAIA incomplete: documento non registrabile")
    payload = record.payload_json or {}
    document = NoticeDocument(
        id=uuid4(),
        source_system=source,
        source_key=str(record.id),
        document_number=str(payload.get("notice_number") or record.id),
        tax_code=avvisi[0].codice_fiscale_raw,
        original_json={
            "generation_id": str(record.id),
            "payload": payload,
            "document_path": record.generated_document_path,
        },
    )
    db.add(document)
    db.flush()
    for avviso in avvisi:
        position = NoticePosition(
            id=uuid4(),
            document_id=document.id,
            source_namespace="gaia",
            source_reference=str(avviso.id),
            tax_year=avviso.anno_tributario,
            avviso_id=avviso.id,
        )
        db.add(position)
        db.flush()
        db.add(NoticeRecovery(position_id=position.id, state="da_verificare"))
    db.add(NoticeNotification(document_id=document.id, state="nessuna_evidenza"))
    db.add(
        NoticeEvidence(
            document_id=document.id,
            source_system=source,
            source_key=str(record.id),
            kind="documento_generato",
            reference=record.generated_document_path,
            original_json=document.original_json,
        )
    )
    db.add(
        NoticeAudit(
            document_id=document.id,
            version=1,
            actor_id=actor_id,
            action="generate_document",
            reason="Generazione documento GAIA, nessun invio",
            before_json={},
            after_json={
                "source_system": source,
                "source_key": str(record.id),
                "avviso_ids": [str(value) for value in avviso_ids],
            },
        )
    )
    db.flush()
    return document


def register_reminder(db, reminder):
    if reminder.status != "draft":
        _publish(db, "gaia_reminder", reminder, [reminder.avviso_id], reminder.generated_by)
    return reminder


def register_batch_item(db, item, *, preview_only: bool) -> None:
    retain_draft_number(db, item)
    if preview_only or item.status not in {"generated", "generated_docx"}:
        return
    batch = db.get(RuoloTributiReminderBatch, item.batch_id)
    _publish(
        db,
        "gaia_batch_item",
        item,
        [UUID(value) for value in item.avviso_ids_json],
        batch.generated_by,
    )
