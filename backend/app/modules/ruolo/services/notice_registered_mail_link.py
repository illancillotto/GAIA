"""Link a verified historical mailing to an existing register scope without duplicating debt."""

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import or_, select, text
from sqlalchemy.orm import Session

from app.modules.ruolo.models import RuoloAvviso, RuoloTributiRegisteredMail
from app.modules.ruolo.notice_register_models import NoticeAttempt, NoticePosition
from app.modules.ruolo.notice_register_schemas import OperatorChange
from app.modules.ruolo.services.notice_register import (
    RegisterConflict,
    RegisterNotFound,
    _audit,
    _document,
    _snapshot,
)
from app.modules.ruolo.services.registered_mail_association import (
    MANUAL_ASSOCIATION_KEY,
    _recovery_status,
    _validate_selected_avvisi,
    associated_avviso_ids,
    get_registered_mail,
    manual_association,
)


def _scope(db: Session, document) -> list[RuoloAvviso]:
    positions = list(
        db.scalars(select(NoticePosition).where(NoticePosition.document_id == document.id))
    )
    position_ids = {position.avviso_id for position in positions}
    if not position_ids or None in position_ids:
        raise RegisterConflict("Il documento deve avere tutte le posizioni collegate ai ruoli")
    avvisi = list(
        db.scalars(
            select(RuoloAvviso)
            .where(RuoloAvviso.id.in_(position_ids))
            .order_by(RuoloAvviso.anno_tributario, RuoloAvviso.id)
            .with_for_update()
        )
    )
    _validate_register_roles(document, positions, avvisi)
    return avvisi


def _validate_register_roles(document, positions, avvisi) -> None:
    _validate_selected_avvisi(avvisi)
    role_scope = {(avviso.id, avviso.anno_tributario) for avviso in avvisi}
    position_scope = {(position.avviso_id, position.tax_year) for position in positions}
    if len(avvisi) != len(positions) or role_scope != position_scope:
        raise RegisterConflict("Posizioni e annualità del documento non coerenti con i ruoli")
    identifiers = {(avviso.codice_fiscale_raw or "").strip().upper() for avviso in avvisi}
    document_identifier = (document.tax_code or "").strip().upper()
    if not document_identifier or identifiers != {document_identifier}:
        raise RegisterConflict("CF del documento non coerente con i ruoli")


def _attempt(db: Session, document, mail: RuoloTributiRegisteredMail) -> NoticeAttempt | None:
    identity = NoticeAttempt.registered_mail_id == mail.id
    if mail.tracking_number:
        identity = or_(identity, NoticeAttempt.tracking_code == mail.tracking_number)
    attempts = list(db.scalars(select(NoticeAttempt).where(identity).with_for_update()))
    if len(attempts) > 1:
        raise RegisterConflict("Più tentativi rivendicano lo stesso invio o tracking")
    if not attempts:
        return None
    attempt = attempts[0]
    if attempt.document_id != document.id or attempt.registered_mail_id not in {None, mail.id}:
        raise RegisterConflict("Tentativo già collegato a un altro documento o invio")
    if (
        attempt.channel not in {"posta", "raccomandata"}
        or attempt.tracking_code != mail.tracking_number
    ):
        raise RegisterConflict("Canale o tracking del tentativo non coerente")
    return attempt


def _lock_tracking(db: Session, mail: RuoloTributiRegisteredMail) -> None:
    if db.get_bind().dialect.name == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtextextended(:identity, 771029))"),
            {"identity": mail.tracking_number or str(mail.id)},
        )


def _validate_mail_scope(mail, avvisi) -> None:
    selected_ids = {avviso.id for avviso in avvisi}
    previous_ids = associated_avviso_ids(mail)
    if previous_ids and previous_ids != selected_ids:
        raise RegisterConflict("Invio già associato a un insieme diverso di avvisi")
    if mail.subject_id not in {None, avvisi[0].subject_id}:
        raise RegisterConflict("Contribuente dell'invio non coerente con il documento")


def _link_is_current(document, mail, attempt, avvisi) -> bool:
    previous = manual_association(mail) or {}
    return (
        attempt is not None
        and attempt.registered_mail_id == mail.id
        and previous.get("notice_document_id") == str(document.id)
        and associated_avviso_ids(mail) == {avviso.id for avviso in avvisi}
        and mail.avviso_id == avvisi[0].id
        and mail.subject_id == avvisi[0].subject_id
        and mail.match_status == "matched"
    )


def associate_registered_mail(
    db: Session, document_id: UUID, mail_id: UUID, change: OperatorChange
) -> RuoloTributiRegisteredMail:
    """Caller owns authorization and transaction; preserve notification and recovery decisions."""
    mail = get_registered_mail(db, mail_id)
    if mail is None:
        raise RegisterNotFound("Raccomandata non trovata")
    _lock_tracking(db, mail)
    document = _document(db, document_id, change)
    avvisi = _scope(db, document)
    _validate_mail_scope(mail, avvisi)
    attempt = _attempt(db, document, mail)
    if _link_is_current(document, mail, attempt, avvisi):
        return mail
    before = {"mail": _snapshot(mail), "attempt": _snapshot(attempt) if attempt else None}
    if attempt is None:
        attempt = NoticeAttempt(
            document_id=document.id,
            registered_mail_id=mail.id,
            source_system="registered_mail_link",
            source_key=str(mail.id),
            channel="raccomandata",
            tracking_code=mail.tracking_number,
            sent_at=mail.sent_at,
        )
        db.add(attempt)
    else:
        attempt.registered_mail_id = mail.id
    mail.raw_payload_json = {
        **(mail.raw_payload_json or {}),
        MANUAL_ASSOCIATION_KEY: {
            "active": True,
            "avviso_id": str(avvisi[0].id),
            "avviso_ids": [str(avviso.id) for avviso in avvisi],
            "notice_document_id": str(document.id),
            "updated_by": change.actor_id,
            "updated_at": datetime.now(UTC).isoformat(),
        },
    }
    mail.avviso_id, mail.subject_id = avvisi[0].id, avvisi[0].subject_id
    mail.match_status, mail.match_score = "matched", 100
    mail.match_reason = "Associazione documentale confermata al Registro dall'operatore"
    mail.anomaly_key = None
    mail.recovery_status = _recovery_status(db, avvisi[0], avvisi=avvisi)
    db.flush()
    _audit(
        db,
        document,
        change,
        {
            "action": "associate_registered_mail",
            "before_json": before,
            "after_json": {"mail": _snapshot(mail), "attempt": _snapshot(attempt)},
        },
    )
    return mail
