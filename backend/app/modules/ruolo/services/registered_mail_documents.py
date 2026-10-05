import hashlib
import re
import uuid
from datetime import UTC, datetime
from pathlib import Path

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso, RuoloTributiRegisteredMail
from app.modules.ruolo.registered_mail_document_models import RegisteredMailDocument
from app.modules.ruolo.registered_mail_document_schemas import (
    CardUpload,
    RegisteredMailDocumentView,
)
from app.modules.ruolo.services.registered_mail_association import associated_avviso_ids
from app.modules.utenze.models import AnagraficaAuditLog, AnagraficaDocument, AnagraficaSubject
from app.modules.utenze.services.import_service import (
    _store_document_on_nas,
    store_uploaded_document,
)
from app.services.nas_connector import get_nas_client

MAX_PDF_BYTES = 20 * 1024 * 1024


def normalized_tracking(value: str | None) -> str:
    raw = (value or "").strip()
    if not re.fullmatch(r"[0-9\s-]+", raw):
        raise HTTPException(422, "Tracking non valido")
    result = re.sub(r"[\s-]", "", raw)
    if len(result) != 12:
        raise HTTPException(422, "Il tracking deve contenere 12 cifre")
    return result


def get_mail(db: Session, mail_id: uuid.UUID, *, lock: bool = False) -> RuoloTributiRegisteredMail:
    query = select(RuoloTributiRegisteredMail).where(RuoloTributiRegisteredMail.id == mail_id)
    mail = db.scalar(query.with_for_update() if lock else query)
    if mail is None:
        raise HTTPException(404, "Raccomandata non trovata")
    return mail


def confirmed_subject(db: Session, mail: RuoloTributiRegisteredMail) -> AnagraficaSubject:
    if "riordino fondiario" in f"{mail.recipient_name} {mail.shipment_name}".lower():
        raise HTTPException(409, "Riordino fondiario escluso")
    if (
        not mail.subject_id
        or not mail.avviso_id
        or mail.match_status != "matched"
        or mail.anomaly_key
    ):
        raise HTTPException(409, "Confermare prima l'associazione al contribuente")
    notices = [db.get(RuoloAvviso, notice_id) for notice_id in associated_avviso_ids(mail)]
    if any(notice is None or notice.subject_id != mail.subject_id for notice in notices):
        raise HTTPException(409, "Identità degli avvisi non coerente")
    subject = db.get(AnagraficaSubject, mail.subject_id)
    if subject is None:
        raise HTTPException(409, "Soggetto non disponibile")
    return subject


def view(link: RegisteredMailDocument, document: AnagraficaDocument) -> RegisteredMailDocumentView:
    return RegisteredMailDocumentView(
        id=link.id,
        document_id=document.id,
        subject_id=document.subject_id,
        filename=document.filename,
        tracking_number=link.tracking_number,
        sha256=link.sha256,
        scanned_on=link.scanned_on,
        source_reference=link.source_reference,
        created_at=link.created_at,
    )


def documents(
    db: Session, mail_id: uuid.UUID
) -> list[tuple[RegisteredMailDocument, AnagraficaDocument]]:
    mail = get_mail(db, mail_id)
    rows = db.execute(
        select(RegisteredMailDocument, AnagraficaDocument)
        .join(AnagraficaDocument, RegisteredMailDocument.document_id == AnagraficaDocument.id)
        .where(RegisteredMailDocument.mail_id == mail_id)
        .order_by(RegisteredMailDocument.created_at, RegisteredMailDocument.id)
    ).all()
    if any(document.subject_id != mail.subject_id for _, document in rows):
        raise HTTPException(409, "Cartoline collegate a un soggetto diverso: revisione necessaria")
    return rows


def validate_subject_change(db: Session, mail_id: uuid.UUID, notices: list[RuoloAvviso]) -> None:
    owners = db.scalars(
        select(AnagraficaDocument.subject_id)
        .join(RegisteredMailDocument, RegisteredMailDocument.document_id == AnagraficaDocument.id)
        .where(RegisteredMailDocument.mail_id == mail_id)
    ).all()
    subjects = {notice.subject_id for notice in notices}
    if any(owner not in subjects for owner in owners):
        raise HTTPException(
            409, "La raccomandata ha cartoline: non cambiare o rimuovere il contribuente"
        )


def store_pdf(subject: AnagraficaSubject, filename: str, content: bytes) -> tuple[str, str | None]:
    local_path = store_uploaded_document(subject.id, filename, content)
    try:
        if not subject.nas_folder_path:
            return local_path, None
        connector = get_nas_client()
        try:
            nas_path = _store_document_on_nas(connector, subject, filename, content)
        finally:
            connector.close()
        return local_path, nas_path
    except Exception:
        Path(local_path).unlink(missing_ok=True)
        raise


def upload(
    db: Session,
    *,
    mail_id: uuid.UUID,
    payload: CardUpload,
    actor_id: int,
) -> RegisteredMailDocumentView:
    filename, content = payload.filename, payload.content
    scanned_on, source_reference = payload.scanned_on, payload.source_reference
    safe_name = Path(filename.replace("\\", "/")).name
    if (
        not safe_name.lower().endswith(".pdf")
        or len(safe_name) > 255
        or not content.startswith(b"%PDF-")
    ):
        raise HTTPException(422, "Caricare una cartolina PDF valida")
    if len(content) > MAX_PDF_BYTES:
        raise HTTPException(413, "PDF superiore a 20 MiB")
    mail = get_mail(db, mail_id, lock=True)
    subject = confirmed_subject(db, mail)
    code = normalized_tracking(payload.tracking_number)
    if code != normalized_tracking(mail.tracking_number):
        raise HTTPException(409, "Tracking cartolina diverso dalla raccomandata")
    digest = hashlib.sha256(content).hexdigest()
    for link, document in documents(db, mail_id):
        if link.sha256 == digest:
            return view(link, document)
    local_path, nas_path = store_pdf(subject, safe_name, content)
    try:
        document = AnagraficaDocument(
            subject_id=subject.id,
            filename=safe_name,
            doc_type="cartolina_raccomandata",
            local_path=local_path,
            nas_path=nas_path,
            storage_type="local_upload",
            mime_type="application/pdf",
            file_size_bytes=len(content),
            classification_source="manual",
            uploaded_at=datetime.now(UTC),
            notes=f"Cartolina raccomandata {code}; scansione {scanned_on.isoformat()}",
        )
        db.add(document)
        db.flush()
        link = RegisteredMailDocument(
            mail_id=mail.id,
            document_id=document.id,
            tracking_number=code,
            sha256=digest,
            scanned_on=scanned_on,
            source_reference=source_reference,
            created_by=actor_id,
        )
        db.add(link)
        db.add(
            AnagraficaAuditLog(
                subject_id=subject.id,
                changed_by_user_id=actor_id,
                action="registered_mail_card_uploaded",
                diff_json={
                    "mail_id": str(mail.id),
                    "document_id": str(document.id),
                    "sha256": digest,
                    "tracking_number": code,
                    "scanned_on": scanned_on.isoformat(),
                    "source_reference": source_reference,
                },
            )
        )
        db.flush()
        result = view(link, document)
        db.commit()
    except Exception:
        db.rollback()
        Path(local_path).unlink(missing_ok=True)
        raise
    return result
