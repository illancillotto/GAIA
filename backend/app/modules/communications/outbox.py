"""Versioned composition and individual authorization, in the caller's transaction."""

from uuid import uuid4

from sqlalchemy import select

from app.modules.ruolo.services.notice_revision import lock_revision, read_revision

from . import registry, ruolo_source, store
from .models import (
    CommunicationAttachment,
    CommunicationAttempt,
    CommunicationAuthorization,
    CommunicationJob,
    CommunicationMessage,
    CommunicationReview,
)
from .policy import (
    EDITABLE,
    Conflict,
    account_fingerprint,
    envelope_digest,
    pdf_pages,
    render_template,
    sha256,
    verify_snapshots,
)
from .source_preview import verify_preview


def _composition(db, payload, source):
    subject, body = payload.subject, payload.body
    if payload.template_id:
        template = registry.approved_template(db, payload.template_id, payload.channel)
        variables = ruolo_source.template_variables(source)
        subject = subject or render_template(template.subject, variables)
        body = body or render_template(template.body, variables)
    if not subject or not body or "\r" in subject or "\n" in subject:
        raise Conflict("Oggetto e testo obbligatori; oggetto su una sola riga")
    return subject, body


def create(db, payload, actor_id):
    if payload.channel == "email" and payload.purpose != "courtesy":
        raise Conflict("Email ordinaria abilitata esclusivamente per cortesia")
    source, document, content, fingerprint = ruolo_source.inspect(db, payload.source_entity_id)
    pages = verify_preview(content, payload.expected_source_sha256)
    account = registry.route_account(db, payload.channel, actor_id, payload.account_id)
    subject, body = _composition(db, payload, source)
    value = CommunicationMessage(
        id=uuid4(),
        source_entity_id=source.id,
        document_id=document.id,
        notice_number=document.document_number,
        channel=payload.channel,
        account_id=account.id,
        account_digest=account_fingerprint(account),
        sender=account.sender,
        recipient=payload.recipient,
        subject=subject,
        body=body,
        template_id=payload.template_id,
        purpose=payload.purpose,
        source_digest=fingerprint,
        created_by=actor_id,
        version=1,
        state="draft",
    )
    db.add(value)
    db.flush()
    db.add(
        CommunicationAttachment(
            message_id=value.id,
            filename=f"avviso-{value.id}.pdf",
            primary_document=True,
            size=len(content),
            sha256=sha256(content),
            pages=pages,
            content=content,
        )
    )
    store.event(db, value.id, "draft_created", actor_id=actor_id, source_digest=fingerprint)
    db.flush()
    return value


def update(db, identity, payload, actor_id):
    value = store.message(db, identity, expected_version=payload.expected_version)
    if value.state not in EDITABLE:
        raise Conflict("Comunicazione non più modificabile; annullare prima della trasmissione")
    if "\r" in payload.subject or "\n" in payload.subject:
        raise Conflict("Oggetto su una sola riga")
    account = registry.route_account(db, value.channel, actor_id, payload.account_id)
    for key in ("account_id", "recipient", "subject", "body"):
        setattr(value, key, getattr(payload, key))
    value.sender, value.account_digest = account.sender, account_fingerprint(account)
    value.version += 1
    value.active_key = None
    if value.state != "draft":
        store.transition(db, value, "draft", actor_id=actor_id)
    store.event(db, value.id, "draft_changed", actor_id=actor_id, version=value.version)
    return value


def verify(db, value, actor_id):
    connection = db.connection()
    revision = read_revision(connection) if connection.dialect.name == "postgresql" else None
    account = registry.route_account(db, value.channel, actor_id, value.account_id)
    if account_fingerprint(account) != value.account_digest:
        raise Conflict("Account cambiato: salvare e ripetere la revisione")
    _, document, content, fingerprint = ruolo_source.inspect(
        db, value.source_entity_id, own_message_id=value.id
    )
    if fingerprint != value.source_digest or document.id != value.document_id:
        raise Conflict("Documento o dati cambiati: annullare e creare una nuova revisione")
    parts = store.attachments(db, value.id)
    verify_snapshots(parts, sha256(content), account.max_bytes, value.body)
    if revision is not None:
        lock_revision(connection, revision)
    return parts


def validate(db, identity, payload, actor_id):
    value = store.message(db, identity, expected_version=payload.expected_version)
    if value.state not in {"draft", "ready"}:
        raise Conflict("Verifica consentita soltanto su una bozza")
    verify(db, value, actor_id)
    if value.state == "draft":
        store.transition(db, value, "ready", actor_id=actor_id)
    store.event(db, value.id, "validated", actor_id=actor_id, version=value.version)
    return value


def start_review(db, value, attachment, actor_id):
    review = CommunicationReview(
        attachment_id=attachment.id, actor_id=actor_id, message_version=value.version
    )
    db.add(review)
    db.flush()
    return review


def add_attachment(db, identity, version, content, actor_id):
    value = store.message(db, identity, expected_version=version)
    if value.state not in EDITABLE:
        raise Conflict("Allegati modificabili solo prima dell'accodamento")
    parts = store.attachments(db, value.id)
    pages = pdf_pages(content)
    if (
        len(parts) >= 10
        or sum(part.size for part in parts) + len(content) > 32 * 1024 * 1024
        or sum(part.pages for part in parts) + pages > 200
    ):
        raise Conflict("Limite complessivo: 10 allegati, 32 MiB e 200 pagine")
    part = CommunicationAttachment(
        message_id=value.id,
        filename=f"allegato-{uuid4()}.pdf",
        primary_document=False,
        size=len(content),
        sha256=sha256(content),
        pages=pages,
        content=content,
    )
    db.add(part)
    value.version += 1
    value.active_key = None
    if value.state != "draft":
        store.transition(db, value, "draft", actor_id=actor_id)
    store.event(
        db,
        value.id,
        "attachment_added",
        actor_id=actor_id,
        sha256=part.sha256,
        version=value.version,
    )
    db.flush()
    return value


def rendered(db, identity, attachment_id, payload, actor_id):
    value = store.message(db, identity, expected_version=payload.expected_version)
    part = next(
        (part for part in store.attachments(db, value.id) if part.id == attachment_id), None
    )
    review = db.get(CommunicationReview, payload.review_id)
    if (
        part is None
        or review is None
        or review.attachment_id != attachment_id
        or review.actor_id != actor_id
        or review.message_version != value.version
        or payload.sha256 != part.sha256
        or payload.pages != part.pages
    ):
        raise Conflict("Attestazione di rendering non valida per questa revisione")
    review.rendered = True
    store.event(
        db,
        value.id,
        "pdf_rendered",
        actor_id=actor_id,
        attachment_id=str(attachment_id),
        version=value.version,
        sha256=part.sha256,
    )
    return value


def approve(db, identity, payload, actor_id):
    value = store.message(db, identity, expected_version=payload.expected_version)
    if value.state != "ready":
        raise Conflict("Verificare la bozza prima dell'approvazione")
    parts = verify(db, value, actor_id)
    for part in parts:
        proof = db.scalar(
            select(CommunicationReview.id)
            .where(
                CommunicationReview.attachment_id == part.id,
                CommunicationReview.actor_id == actor_id,
                CommunicationReview.message_version == value.version,
                CommunicationReview.rendered.is_(True),
            )
            .limit(1)
        )
        if proof is None:
            raise Conflict("Rendering integrale del PDF non confermato per l'operatore")
    value.active_key = value.notice_number
    db.add(
        CommunicationAuthorization(
            message_id=value.id,
            version=value.version,
            actor_id=actor_id,
            digest=envelope_digest(value, parts),
            checklist=payload.checklist,
        )
    )
    store.transition(db, value, "approved", actor_id=actor_id)
    db.flush()
    return value


def dispatch(db, identity, payload, actor_id):
    value = store.message(db, identity, expected_version=payload.expected_version)
    existing = db.scalar(
        select(CommunicationJob).where(
            CommunicationJob.idempotency_key == f"dispatch:{value.id}:{value.version}"
        )
    )
    if existing:
        return existing
    if value.state != "approved":
        raise Conflict("Autorizzazione individuale obbligatoria")
    parts = verify(db, value, actor_id)
    authorization(db, value, parts)
    job = CommunicationJob(
        message_id=value.id,
        account_id=value.account_id,
        kind=f"dispatch_{value.channel}",
        idempotency_key=f"dispatch:{value.id}:{value.version}",
    )
    db.add(job)
    store.transition(db, value, "queued", actor_id=actor_id)
    db.flush()
    return job


def authorization(db, value, parts):
    result = db.scalar(
        select(CommunicationAuthorization).where(
            CommunicationAuthorization.message_id == value.id,
            CommunicationAuthorization.version == value.version,
        )
    )
    if result is None or result.digest != envelope_digest(value, parts):
        raise Conflict("Autorizzazione assente o non coerente con il messaggio")
    return result


def cancel(db, identity, payload, actor_id):
    value = store.message(db, identity, expected_version=payload.expected_version)
    unsafe = db.scalar(
        select(CommunicationAttempt.id)
        .where(
            CommunicationAttempt.message_id == value.id,
            CommunicationAttempt.state.in_(("sending", "submitted", "uncertain")),
        )
        .limit(1)
    )
    if unsafe:
        raise Conflict("Trasmissione iniziata o incerta: annullamento non consentito")
    store.transition(db, value, "cancelled", actor_id=actor_id)
    value.active_key = None
    for job in db.scalars(
        select(CommunicationJob)
        .where(
            CommunicationJob.message_id == value.id,
            CommunicationJob.state.in_(("pending", "processing")),
        )
        .with_for_update()
    ):
        job.state = "cancelled"
    return value
